"""Мост llama.cpp -> Ollama.

Зачем: весь agent.py и app.py умеют говорить только протоколом Ollama (/api/chat, /api/tags,
NDJSON-строки при стриминге). Переписывать их ради другого движка — плодить баги. Вместо этого
этот файл поднимает свой собственный маленький сервер, который:
  1) сам запускает настоящий llama-server.exe (движок llama.cpp, без Ollama) и следит, чтобы он жил;
  2) снаружи отвечает ТОЧНО как Ollama (/api/tags, /api/chat), а внутри дергает llama.cpp.

В итоге в data/config.json меняется только ollama_url — он указывает на порт этого моста,
а не на настоящую Ollama. Остальной код проекта не замечает подмены.

Настройки живут в data/llamacpp.json:
  exe        - путь к llama-server.exe (скачивается отдельно, см. LLAMACPP_SETUP.txt)
  model      - путь к файлу модели .gguf (скачивается отдельно)
  model_name - как модель будет называться в интерфейсе (что угодно, просто имя)
  gpu_layers - сколько слоёв модели выгружать на видеокарту; 0 = считать на CPU (медленно)
  ctx        - размер контекста (окно памяти диалога)
  backend_port - порт настоящего llama-server (внутренний, трогать не нужно)
  bridge_port  - порт этого моста = тот самый "ollama_url" порт
"""
import json, re, subprocess, sys, threading, time
from pathlib import Path

import requests
from flask import Flask, Response, jsonify, request, stream_with_context

BASE = Path(__file__).resolve().parent
DATA = BASE / "data"; DATA.mkdir(parents=True, exist_ok=True)
CFG_FILE = DATA / "llamacpp.json"
LOG = DATA / "llamacpp_bridge.log"

DEFAULT = {
    "exe": str(BASE / "llamacpp" / "llama-server.exe"),
    "model": str(BASE / "models" / "model.gguf"),
    "model_name": "local-gguf",
    "gpu_layers": 999,   # 999 = выгрузить всю модель на GPU, если влезает; не влезет - llama.cpp сам подрежет
    "ctx": 8192,
    "backend_port": 8081,
    "bridge_port": 8090,
}


def cfg():
    try:
        d = json.loads(CFG_FILE.read_text(encoding="utf-8"))
    except Exception:
        d = {}
    out = {**DEFAULT, **d}
    if not CFG_FILE.exists():
        CFG_FILE.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def log(msg):
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    try:
        with LOG.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


# -------------------------------------------------- управление процессом llama-server.exe
_proc = None
_proc_lock = threading.Lock()


def backend_alive(c):
    try:
        r = requests.get(f"http://127.0.0.1:{c['backend_port']}/health", timeout=2)
        return r.status_code == 200
    except Exception:
        return False


def start_backend():
    c = cfg()
    with _proc_lock:
        global _proc
        if _proc is not None and _proc.poll() is None:
            return
        exe, model = Path(c["exe"]), Path(c["model"])
        if not exe.exists():
            raise RuntimeError(f"Не найден llama-server.exe: {exe}\nСм. LLAMACPP_SETUP.txt — его нужно скачать отдельно.")
        if not model.exists():
            raise RuntimeError(f"Не найден файл модели: {model}\nСм. LLAMACPP_SETUP.txt — .gguf скачивается отдельно.")
        cmd = [str(exe), "-m", str(model), "--port", str(c["backend_port"]), "--host", "127.0.0.1",
               "-c", str(int(c["ctx"])), "-ngl", str(int(c["gpu_layers"])), "--no-webui"]
        log("Запускаю: " + " ".join(cmd))
        logf = open(LOG, "a", encoding="utf-8")
        _proc = subprocess.Popen(cmd, cwd=str(BASE), stdout=logf, stderr=subprocess.STDOUT)
    for _ in range(150):  # до ~75 сек на загрузку модели в память
        if backend_alive(c):
            log("llama-server готов."); return
        if _proc.poll() is not None:
            raise RuntimeError("llama-server.exe завершился при старте. Смотри data/llamacpp_bridge.log")
        time.sleep(0.5)
    raise RuntimeError("llama-server не ответил за 75 секунд (большая модель грузится дольше - подожди и спроси снова).")


def watchdog():
    while True:
        time.sleep(5)
        c = cfg()
        if _proc is not None and _proc.poll() is not None:
            log("llama-server упал, перезапускаю...")
            try:
                start_backend()
            except Exception as e:
                log(f"Перезапуск не удался: {e}")


# -------------------------------------------------- перевод Ollama <-> llama.cpp (OpenAI-формат)
def to_openai_messages(messages):
    return [{"role": m.get("role", "user"), "content": str(m.get("content", ""))} for m in messages]


app = Flask(__name__)


@app.get("/health")
def health():
    return jsonify(ok=True, backend=backend_alive(cfg()))


@app.get("/api/tags")
def tags():
    c = cfg()
    return jsonify(models=[{"name": c["model_name"], "model": c["model_name"]}])


@app.post("/api/chat")
def chat():
    return _chat_impl(request.get_json(silent=True) or {})


@app.post("/api/generate")
def generate():
    """Запасной путь на случай старого кода, который просит /api/generate вместо /api/chat."""
    d = request.get_json(silent=True) or {}
    d["messages"] = [{"role": "user", "content": d.get("prompt", "")}]
    return _chat_impl(d)


def _chat_impl(d):
    c = cfg()
    try:
        if not backend_alive(c):
            start_backend()
    except Exception as e:
        return jsonify(error=str(e)), 502

    stream = bool(d.get("stream", True))
    opt = d.get("options", {}) or {}
    payload = {
        "model": c["model_name"],
        "messages": to_openai_messages(d.get("messages", [])),
        "stream": stream,
        "temperature": float(opt.get("temperature", 0.25)),
        "top_p": float(opt.get("top_p", 0.92)),
        "top_k": int(opt.get("top_k", 40)),
        "repeat_penalty": float(opt.get("repeat_penalty", 1.08)),
        "n_predict": int(opt.get("num_predict", 1500)),
    }
    url = f"http://127.0.0.1:{c['backend_port']}/v1/chat/completions"

    if not stream:
        r = requests.post(url, json=payload, timeout=(5, 600))
        r.raise_for_status()
        text = r.json()["choices"][0]["message"]["content"]
        return jsonify(message={"role": "assistant", "content": text}, done=True)

    def gen():
        r = requests.post(url, json=payload, stream=True, timeout=(5, 600))
        if r.status_code >= 400:
            yield json.dumps({"message": {"role": "assistant", "content": ""}, "done": True,
                               "error": f"llama.cpp: HTTP {r.status_code}"}) + "\n"
            return
        for raw in r.iter_lines(decode_unicode=True):
            if not raw or not raw.startswith("data: "):
                continue
            data = raw[6:]
            if data.strip() == "[DONE]":
                yield json.dumps({"message": {"role": "assistant", "content": ""}, "done": True}) + "\n"
                return
            try:
                obj = json.loads(data)
                piece = obj["choices"][0].get("delta", {}).get("content", "")
            except Exception:
                piece = ""
            if piece:
                yield json.dumps({"message": {"role": "assistant", "content": piece}, "done": False}) + "\n"
        yield json.dumps({"message": {"role": "assistant", "content": ""}, "done": True}) + "\n"

    return Response(stream_with_context(gen()), mimetype="application/x-ndjson")


if __name__ == "__main__":
    c = cfg()
    log(f"Мост запущен. Телефон/программа подключаются на http://127.0.0.1:{c['bridge_port']} (как раньше к Ollama).")
    try:
        start_backend()
    except Exception as e:
        log(f"ВНИМАНИЕ: движок не стартовал сразу: {e}")
        log("Исправь путь к exe/модели в data/llamacpp.json и перезапусти этот файл.")
    threading.Thread(target=watchdog, daemon=True).start()
    app.run(host="127.0.0.1", port=int(c["bridge_port"]), threaded=True)
