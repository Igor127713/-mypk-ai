import json, os, socket, subprocess, sys, time, urllib.request, webbrowser
from pathlib import Path
BASE=Path(__file__).resolve().parent
LOG=BASE/"startup.log"
CFG=BASE/"data"/"config.json"

def cfg():
    try: return json.loads(CFG.read_text(encoding="utf-8"))
    except Exception: return {}

def write_cfg(c):
    CFG.parent.mkdir(parents=True, exist_ok=True)
    CFG.write_text(json.dumps(c, ensure_ascii=False, indent=2), encoding="utf-8")

def free_port(start):
    for p in range(start, start+50):
        s=socket.socket();
        try:
            s.bind(("127.0.0.1",p)); s.close(); return p
        except OSError:
            s.close()
    raise RuntimeError("Не удалось найти свободный порт")

def alive(p):
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{p}/health", timeout=1.5) as r: return r.status == 200
    except Exception: return False

c=cfg(); p=int(c.get("port",7860) or 7860)
print("=== MYPK AI 9 START ===", flush=True)
print("Python:", sys.version.split()[0], flush=True)
if not alive(p):
    test=socket.socket()
    try: test.bind(("127.0.0.1",p)); occupied=False
    except OSError: occupied=True
    finally: test.close()
    if occupied:
        p=free_port(p+1); c["port"]=p; write_cfg(c); print(f"[INFO] Порт занят, использую {p}.", flush=True)
    LOG.write_text("=== MYPK AI 9 startup ===\n", encoding="utf-8")
    with LOG.open("a",encoding="utf-8") as log:
        proc=subprocess.Popen([sys.executable, str(BASE/"app.py")], cwd=str(BASE), stdout=log, stderr=subprocess.STDOUT)
    for _ in range(50):
        if alive(p): break
        if proc.poll() is not None: break
        time.sleep(.4)
    if not alive(p):
        print("[ERROR] Сервер не запустился.", flush=True)
        try: print(LOG.read_text(encoding="utf-8", errors="replace")[-20000:], flush=True)
        except Exception as e: print(e, flush=True)
        raise SystemExit(1)
print(f"[OK] Сервер: http://127.0.0.1:{p}", flush=True)
try:
    s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM); s.connect(("1.1.1.1",80)); ip=s.getsockname()[0]; s.close()
except Exception: ip="127.0.0.1"
(BASE/"data"/"runtime_port.txt").write_text(str(p),encoding="utf-8")
(BASE/"data"/"runtime_ip.txt").write_text(ip,encoding="utf-8")
print(f"[LAN] http://{ip}:{p}", flush=True)
(BASE/"data"/"public_url.txt").unlink(missing_ok=True)
pwf=BASE/"data"/"PASSWORD.txt"
if pwf.exists():
    print("-"*50, flush=True)
    print(pwf.read_text(encoding="utf-8"), flush=True)
    print("(файл: data\\PASSWORD.txt)", flush=True)
    print("-"*50, flush=True)
if not os.environ.get("MYPK_NO_BROWSER"):
    webbrowser.open(f"http://127.0.0.1:{p}")
print("READY", flush=True)
