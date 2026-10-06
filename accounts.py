"""Аккаунты: админ (владелец ПК) и обычные пользователи.

Хранится в data/users.json: {имя: {salt, hash, role, created}}.
История вопрос-ответ каждого пользователя - в data/history/<имя>.jsonl, по одной строке на обмен.
Пароли не хранятся в открытом виде - только соль и SHA-256 от (соль+пароль).

Важно про права: роль "admin" всего одна - это владелец ПК (ты). Все, кто регистрируется сам -
всегда роль "user". У "user" НЕТ доступа к управлению ПК, памяти ИИ и расширениям, даже если
они включены в настройках: это решается на уровне app.py/agent.py (admin_auth, role в agent_stream),
а не здесь - этот файл только хранит, кто есть кто.
"""
import hashlib, json, re, secrets, time
from pathlib import Path

DATA = None
USERS_FILE = None
HIST_DIR = None


def setup(data_dir: Path):
    global DATA, USERS_FILE, HIST_DIR
    DATA = data_dir
    USERS_FILE = DATA / "users.json"
    HIST_DIR = DATA / "history"
    HIST_DIR.mkdir(parents=True, exist_ok=True)


def _hash(pw, salt):
    return hashlib.sha256((salt + str(pw)).encode("utf-8")).hexdigest()


def _load():
    try:
        return json.loads(USERS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save(u):
    USERS_FILE.write_text(json.dumps(u, ensure_ascii=False, indent=2), encoding="utf-8")


def ensure_admin(admin_password):
    """Первый запуск: создаёт единственного админа с текущим паролем программы."""
    u = _load()
    if not u:
        salt = secrets.token_hex(8)
        u["admin"] = {"salt": salt, "hash": _hash(admin_password, salt), "role": "admin", "created": int(time.time())}
        _save(u)
    return u


def verify(username, password):
    u = _load().get(str(username).strip())
    if not u or _hash(password, u["salt"]) != u["hash"]:
        return None
    return u["role"]


NAME_RE = re.compile(r"^[a-zA-Zа-яА-ЯёЁ0-9_\-]{3,32}$")


def create_user(username, password, role="user"):
    username = str(username).strip()
    if not NAME_RE.match(username):
        raise ValueError("Имя пользователя: 3-32 символа, буквы/цифры/_/-, без пробелов.")
    if len(str(password)) < 6:
        raise ValueError("Пароль должен быть не короче 6 символов.")
    u = _load()
    if username in u:
        raise ValueError("Это имя уже занято.")
    salt = secrets.token_hex(8)
    u[username] = {"salt": salt, "hash": _hash(password, salt), "role": role, "created": int(time.time())}
    _save(u)
    return username


def set_password(username, new_password):
    u = _load()
    if username not in u:
        raise ValueError("Нет такого пользователя.")
    if len(str(new_password)) < 6:
        raise ValueError("Пароль должен быть не короче 6 символов.")
    salt = secrets.token_hex(8)
    u[username]["salt"] = salt
    u[username]["hash"] = _hash(new_password, salt)
    _save(u)


def delete_user(username):
    u = _load()
    if username in u and u[username]["role"] != "admin":
        del u[username]
        _save(u)
        try:
            (_hist_file(username)).unlink()
        except Exception:
            pass


def _safe(name):
    return re.sub(r"[^a-zA-Zа-яА-ЯёЁ0-9_\-]", "_", str(name))[:40]


def _hist_file(username):
    return HIST_DIR / f"{_safe(username)}.jsonl"


def log_turn(username, question, answer):
    """Добавляет одну пару вопрос-ответ в историю пользователя. Тихо игнорирует ошибки -
    история вспомогательная вещь, из-за неё не должен падать сам ответ ИИ."""
    if not username or not (question or answer):
        return
    try:
        line = json.dumps({"ts": int(time.time()), "q": str(question)[:4000], "a": str(answer)[:8000]},
                           ensure_ascii=False)
        f = _hist_file(username)
        with f.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
        _trim(f, 500)
    except Exception:
        pass


def _trim(f, keep):
    try:
        lines = f.read_text(encoding="utf-8").splitlines()
        if len(lines) > keep:
            f.write_text("\n".join(lines[-keep:]) + "\n", encoding="utf-8")
    except Exception:
        pass


def count_turns(username):
    try:
        with _hist_file(username).open(encoding="utf-8") as f:
            return sum(1 for _ in f)
    except Exception:
        return 0


def read_history(username, limit=300):
    out = []
    try:
        lines = _hist_file(username).read_text(encoding="utf-8").splitlines()[-limit:]
        for ln in lines:
            try:
                out.append(json.loads(ln))
            except Exception:
                pass
    except Exception:
        pass
    out.reverse()  # новые сверху
    return out


def list_users():
    u = _load()
    out = [{"username": name, "role": d.get("role", "user"), "created": d.get("created", 0),
            "turns": count_turns(name)} for name, d in u.items()]
    out.sort(key=lambda x: (x["role"] != "admin", -x["created"]))
    return out
