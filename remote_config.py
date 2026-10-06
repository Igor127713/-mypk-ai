import json
from pathlib import Path
base = Path(__file__).resolve().parent
p = base / 'data' / 'config.json'
try:
    c = json.loads(p.read_text(encoding='utf-8')) if p.exists() else {}
except Exception:
    c = {}
port = int(c.get('port', 7860))
password_changed = c.get('password', 'admin') != 'admin'
print(port, 'CHANGED' if password_changed else 'DEFAULT')
