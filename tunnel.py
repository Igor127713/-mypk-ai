"""Starts a Cloudflare quick tunnel and publishes its address (data/public_url.txt) so the app can show it."""
import re, subprocess, sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
URL_FILE = BASE / "data" / "public_url.txt"
URL_RE = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")

def find_url(line):
    m = URL_RE.search(line)
    return m.group(0) if m else None

def main():
    port = sys.argv[1] if len(sys.argv) > 1 else "7860"
    exe = BASE / "cloudflared.exe"
    cmd = [str(exe) if exe.exists() else "cloudflared", "tunnel", "--no-autoupdate", "--url", f"http://127.0.0.1:{port}"]
    URL_FILE.parent.mkdir(parents=True, exist_ok=True)
    URL_FILE.unlink(missing_ok=True)
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
    shown = False
    try:
        for line in proc.stdout:
            url = find_url(line)
            if url and not shown:
                shown = True
                URL_FILE.write_text(url, encoding="utf-8")
                print("\n" + "=" * 60)
                print("  АДРЕС ДЛЯ ТЕЛЕФОНА (откройте в браузере):")
                print("  " + url)
                print("  Логин не нужен, только пароль из data\\PASSWORD.txt")
                print("  Адрес меняется при каждом запуске туннеля.")
                print("=" * 60 + "\n", flush=True)
            elif not shown:
                print(line.rstrip(), flush=True)
    except KeyboardInterrupt:
        pass
    finally:
        proc.terminate()
        URL_FILE.unlink(missing_ok=True)

if __name__ == "__main__":
    main()
