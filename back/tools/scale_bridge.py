import os
import time
import re
import requests
import serial

API_URL = os.getenv("SCANNER_PUBLIC_URL", "http://localhost:8000/scanner/evento/public")
SCANNER_KEY = os.getenv("SCANNER_KEY", "")
COM_PORT = os.getenv("SCANNER_COM_PORT", "COM3")
BAUD_RATE = int(os.getenv("SCANNER_BAUD_RATE", "9600"))
MIN_INTERVAL_MS = int(os.getenv("SCANNER_MIN_INTERVAL_MS", "500"))
DELTA_THRESHOLD = float(os.getenv("SCANNER_DELTA_THRESHOLD", "0.005"))

def parse_weight(s: str) -> float | None:
    m = re.search(r"-?\d+(?:[.,]\d+)?", s)
    if not m:
        return None
    v = m.group(0).replace(",", ".")
    try:
        return float(v)
    except ValueError:
        return None

def post_weight(w: float) -> bool:
    try:
        r = requests.post(
            API_URL,
            json={"peso": w, "nombre": "Balanza"},
            headers={"X-Scanner-Key": SCANNER_KEY},
            timeout=3,
        )
        return r.ok
    except Exception:
        return False

def main():
    last_sent = None
    last_ts = 0.0
    while True:
        try:
            with serial.Serial(COM_PORT, BAUD_RATE, timeout=1) as ser:
                while True:
                    raw = ser.readline()
                    if not raw:
                        continue
                    try:
                        s = raw.decode("utf-8", errors="ignore").strip()
                    except Exception:
                        continue
                    w = parse_weight(s)
                    if w is None:
                        continue
                    now = time.time() * 1000.0
                    if last_sent is None or abs(w - last_sent) >= DELTA_THRESHOLD or (now - last_ts) >= MIN_INTERVAL_MS:
                        if post_weight(w):
                            last_sent = w
                            last_ts = now
        except Exception:
            time.sleep(1.0)

if __name__ == "__main__":
    main()
