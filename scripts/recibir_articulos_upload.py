#!/usr/bin/env python3
"""Recibe articulos.xls por HTTP y lo guarda en datos /articulos.xls"""
from __future__ import annotations

import cgi
import hashlib
import http.server
import os
import socketserver
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEST = ROOT / "datos /articulos.xls"
TOKEN = os.environ.get("UPLOAD_TOKEN", "ima-articulos-2026")
PORT = int(os.environ.get("UPLOAD_PORT", "9876"))
HOST = os.environ.get("UPLOAD_HOST", "0.0.0.0")


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if f"token={TOKEN}" not in self.path:
            self.send_error(403, "Token inválido")
            return
        html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Subir articulos.xls</title></head>
<body style="font-family:sans-serif;max-width:520px;margin:40px auto">
<h2>Subir articulos.xls al servidor</h2>
<form method="POST" enctype="multipart/form-data">
<input type="hidden" name="token" value="{TOKEN}">
<input type="file" name="archivo" accept=".xls,.xlsx" required>
<button type="submit">Subir</button>
</form>
<p>Destino: <code>{DEST}</code></p>
</body></html>"""
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode())

    def do_POST(self) -> None:
        ctype = self.headers.get("Content-Type", "")
        if "multipart/form-data" not in ctype:
            self.send_error(400, "Se espera multipart/form-data")
            return
        form = cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={
                "REQUEST_METHOD": "POST",
                "CONTENT_TYPE": ctype,
            },
        )
        if form.getvalue("token") != TOKEN:
            self.send_error(403, "Token inválido")
            return
        item = form["archivo"] if "archivo" in form else None
        if item is None or not getattr(item, "file", None):
            self.send_error(400, "Falta archivo")
            return
        data = item.file.read()
        if len(data) < 10_000:
            self.send_error(400, "Archivo demasiado chico")
            return
        DEST.parent.mkdir(parents=True, exist_ok=True)
        DEST.write_bytes(data)
        digest = hashlib.sha256(data).hexdigest()[:12]
        msg = f"OK: {len(data)} bytes guardados en {DEST} (sha256…{digest})"
        print(msg, flush=True)
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(msg.encode())

    def log_message(self, fmt: str, *args) -> None:
        print(f"[upload] {self.address_string()} - {fmt % args}", flush=True)


def main() -> int:
    DEST.parent.mkdir(parents=True, exist_ok=True)
    with socketserver.TCPServer((HOST, PORT), Handler) as httpd:
        url = f"http://164.68.118.75:{PORT}/?token={TOKEN}"
        print(f"Esperando articulos.xls en {url}", flush=True)
        print(f"Destino: {DEST}", flush=True)
        httpd.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
