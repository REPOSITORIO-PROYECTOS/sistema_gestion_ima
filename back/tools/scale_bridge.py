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

def parse_weight_and_price(s: str) -> tuple[float | None, float | None]:
    # Reemplazamos comas por puntos para normalizar
    normalized = s.replace(",", ".")
    # Buscamos todos los números decimales
    matches = re.findall(r"-?\d+(?:\.\d+)?", normalized)
    
    if not matches:
        return None, None
    
    try:
        peso = float(matches[0])
        precio = float(matches[1]) if len(matches) >= 2 else None
        return peso, precio
    except ValueError:
        return None, None

def post_weight(w: float, p: float | None = None) -> bool:
    try:
        payload = {"peso": w, "nombre": "Balanza"}
        if p is not None:
            payload["precio"] = p
            
        r = requests.post(
            API_URL,
            json=payload,
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
                    
                    w, p = parse_weight_and_price(s)
                    if w is None:
                        continue
                        
                    now = time.time() * 1000.0
                    if last_sent is None or abs(w - last_sent) >= DELTA_THRESHOLD or (now - last_ts) >= MIN_INTERVAL_MS:
                        if post_weight(w, p):
                            last_sent = w
                            last_ts = now
        except Exception:
            time.sleep(1.0)

if __name__ == "__main__":
    main()