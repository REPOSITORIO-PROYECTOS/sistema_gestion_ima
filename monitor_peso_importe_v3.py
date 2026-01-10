
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Monitor Serie GUI - Pesaje/Importe (v3)
---------------------------------------
- PESO (izquierda) con 3 decimales fijos, color negro, ~2 cm.
- IMPORTE (derecha) con hasta 2 decimales (sin ceros sobrantes), color azul, ~2 cm.
- Botón Conectar/Desconectar arriba a la derecha:
    * Verde cuando está DESCONECTADO (texto "Conectar")
    * Rojo cuando está CONECTADO (texto "Desconectar")
- Botón ⚙ Configuración abajo a la derecha.
- Fondo gris claro.
- Baud 9600 y ASCII fijos (no modificables).

Requisitos:
    pip install pyserial

Ejecución:
    python monitor_peso_importe_v3.py
"""
import threading
import queue
import time
import re
import tkinter as tk
from tkinter import ttk, messagebox
from tkinter import font as tkfont

try:
    import serial
    import serial.tools.list_ports as list_ports
except Exception:
    serial = None
    list_ports = None

BAUD_RATE = 9600
ENCODING = "ascii"
BG_COLOR = "#f2f2f2"  # gris claro
BTN_GREEN = "#22c55e"  # desconectado -> conectar
BTN_RED   = "#ef4444"  # conectado -> desconectar

def cm_to_points(cm: float) -> int:
    # 1 inch = 2.54 cm ; 1 pt = 1/72 inch
    return int(round(cm * 72.0 / 2.54))

BIG_PT = cm_to_points(2.0)  # ~2 cm

class SerialReader(threading.Thread):
    def __init__(self, ser, out_queue, stop_event):
        super().__init__(daemon=True)
        self.ser = ser
        self.out_queue = out_queue
        self.stop_event = stop_event

    def run(self):
        buffer = bytearray()
        while not self.stop_event.is_set():
            try:
                if self.ser.in_waiting:
                    data = self.ser.read(self.ser.in_waiting)
                    buffer.extend(data)
                    while True:
                        idx = buffer.find(b'\n')
                        if idx == -1:
                            break
                        line = buffer[:idx+1]
                        del buffer[:idx+1]
                        try:
                            text = line.decode(ENCODING, errors='ignore')
                        except Exception:
                            text = line.decode('utf-8', errors='ignore')
                        self.out_queue.put(text)
                else:
                    time.sleep(0.01)
            except Exception as e:
                self.out_queue.put(f"[ERROR lector] {e}\n")
                break

class ConfigDialog(tk.Toplevel):
    def __init__(self, master, current_port):
        super().__init__(master)
        self.title("Configuración")
        self.configure(bg=BG_COLOR)
        self.resizable(False, False)
        self.grab_set()
        self.focus_set()

        self.port_var = tk.StringVar(value=current_port or "")

        frm = ttk.Frame(self, padding=12)
        frm.pack(fill="both", expand=True)

        ttk.Label(frm, text="Puerto COM:").grid(row=0, column=0, sticky="w")
        self.port_cb = ttk.Combobox(frm, textvariable=self.port_var, width=28, state="readonly")
        self.port_cb.grid(row=0, column=1, padx=6, pady=4, sticky="ew")

        ttk.Button(frm, text="Refrescar", command=self.refresh_ports).grid(row=0, column=2, padx=6, pady=4)

        ttk.Label(frm, text=f"Baud: {BAUD_RATE} (fijo)").grid(row=1, column=0, columnspan=3, sticky="w", pady=(8,0))
        ttk.Label(frm, text=f"Codificación: {ENCODING.upper()} (fijo)").grid(row=2, column=0, columnspan=3, sticky="w")

        btns = ttk.Frame(frm)
        btns.grid(row=3, column=0, columnspan=3, pady=(12,0), sticky="e")
        ttk.Button(btns, text="Cancelar", command=self._cancel).pack(side="right", padx=4)
        ttk.Button(btns, text="Aceptar", command=self._accept).pack(side="right", padx=4)

        frm.columnconfigure(1, weight=1)
        self.refresh_ports()

    def refresh_ports(self):
        ports = []
        if list_ports is not None:
            try:
                for p in list_ports.comports():
                    ports.append(f"{p.device} - {p.description}")
            except Exception:
                pass
        self.port_cb["values"] = ports
        if ports and not self.port_var.get():
            self.port_var.set(ports[0])

    def _parse_selected_port(self):
        sel = (self.port_var.get() or "").strip()
        return sel.split(" - ",1)[0] if " - " in sel else sel

    def _accept(self):
        self.result = self._parse_selected_port()
        self.destroy()

    def _cancel(self):
        self.result = None
        self.destroy()

class App(tk.Tk):
    NUM_RE = re.compile(r'[-+]?\d+(?:[.,]\d+)?')
    def __init__(self):
        super().__init__()
        self.title("Monitor Serie - Peso/Importe")
        self.configure(bg=BG_COLOR)
        self.geometry("900x430")
        self.minsize(720, 340)

        self.selected_port = ""
        self.ser = None
        self.reader = None
        self.stop_event = threading.Event()
        self.queue = queue.Queue()

        self.big_font = tkfont.Font(family="Consolas", size=BIG_PT, weight="bold")

        self._build_ui()
        self.after(30, self._poll_queue)
        self.protocol("WM_DELETE_WINDOW", self.on_exit)

    def _build_ui(self):
        # Barra superior con botón Conectar/Desconectar a la derecha
        top = tk.Frame(self, bg=BG_COLOR)
        top.pack(side="top", fill="x")

        self.conn_btn = tk.Button(
            top, text="Conectar", command=self.toggle_connection,
            fg="white", bg=BTN_GREEN,
            activeforeground="white", activebackground=BTN_GREEN,
            relief="raised", padx=12, pady=6
        )
        self.conn_btn.pack(side="right", padx=10, pady=8)

        # Panel central con dos valores grandes
        panel = tk.Frame(self, bg=BG_COLOR, padx=12, pady=8)
        panel.pack(side="top", fill="both", expand=True)

        left = tk.Frame(panel, bg=BG_COLOR)
        left.pack(side="left", fill="both", expand=True, padx=(0,8))

        right = tk.Frame(panel, bg=BG_COLOR)
        right.pack(side="right", fill="both", expand=True, padx=(8,0))

        tk.Label(left, text="PESO", bg=BG_COLOR, fg="#333333", font=("Segoe UI", 16, "bold")).pack(anchor="center", pady=(0,6))
        tk.Label(right, text="IMPORTE", bg=BG_COLOR, fg="#333333", font=("Segoe UI", 16, "bold")).pack(anchor="center", pady=(0,6))

        self.peso_var = tk.StringVar(value="—")
        self.importe_var = tk.StringVar(value="—")

        tk.Label(left, textvariable=self.peso_var, bg=BG_COLOR, fg="#000000", font=self.big_font).pack(expand=True)
        tk.Label(right, textvariable=self.importe_var, bg=BG_COLOR, fg="#0066cc", font=self.big_font).pack(expand=True)

        # Barra inferior con estado y ⚙ Configuración a la derecha
        bottom = tk.Frame(self, bg=BG_COLOR)
        bottom.pack(side="bottom", fill="x")

        self.status = tk.StringVar(value="Listo")
        ttk.Label(bottom, textvariable=self.status, anchor="w", padding=(8,2)).pack(side="left", fill="x", expand=True)

        ttk.Button(bottom, text="⚙ Configuración", command=self.open_config).pack(side="right", padx=10, pady=8)

        # Estilo ttk
        try:
            style = ttk.Style()
            for theme in ("clam","vista","default"):
                if theme in style.theme_names():
                    style.theme_use(theme); break
        except Exception:
            pass

    def _update_conn_btn(self, connected: bool):
        if connected:
            self.conn_btn.configure(text="Desconectar", bg=BTN_RED, activebackground=BTN_RED)
        else:
            self.conn_btn.configure(text="Conectar", bg=BTN_GREEN, activebackground=BTN_GREEN)

    def open_config(self):
        if serial is None:
            messagebox.showerror("Error","pyserial no está instalado.\nInstala con: pip install pyserial")
            return
        dlg = ConfigDialog(self, self.selected_port)
        self.wait_window(dlg)
        if getattr(dlg, "result", None):
            self.selected_port = dlg.result
            self.status.set(f"Puerto: {self.selected_port} @ {BAUD_RATE} {ENCODING.upper()}")

    def toggle_connection(self):
        if self.ser is None:
            self.connect()
        else:
            self.disconnect()

    def connect(self):
        if serial is None:
            messagebox.showerror("Error","pyserial no está instalado.\nInstala con: pip install pyserial")
            return
        if not self.selected_port:
            messagebox.showwarning("Atención","Seleccioná un puerto COM en Configuración.")
            return
        try:
            self.ser = serial.Serial(port=self.selected_port, baudrate=BAUD_RATE, timeout=0.05)
            self.stop_event.clear()
            self.reader = SerialReader(self.ser, self.queue, self.stop_event)
            self.reader.start()
            self._update_conn_btn(True)
            self.status.set(f"Conectado a {self.selected_port} @ {BAUD_RATE} (ASCII)")
        except Exception as e:
            self.ser = None
            messagebox.showerror("Error al conectar", str(e))

    def disconnect(self):
        try:
            if self.reader and self.reader.is_alive():
                self.stop_event.set()
                self.reader.join(timeout=1.0)
        except Exception:
            pass
        try:
            if self.ser and self.ser.is_open:
                self.ser.close()
        except Exception:
            pass
        self.ser = None
        self.reader = None
        self._update_conn_btn(False)
        self.status.set("Desconectado")

    def _poll_queue(self):
        try:
            while True:
                self._handle_line(self.queue.get_nowait())
        except queue.Empty:
            pass
        self.after(30, self._poll_queue)

    def _handle_line(self, text: str):
        t = text.strip()
        if not t:
            return
        # Buscar dos números (peso e importe). Soporta "123.45, 678.9" o "123,45 678.90"
        nums = self.NUM_RE.findall(t.replace(",", "."))
        if len(nums) >= 2:
            try:
                peso = float(nums[0])
                imp  = float(nums[1])
                self.peso_var.set(self._fmt_peso(peso))
                self.importe_var.set(self._fmt_importe(imp))
            except Exception:
                pass

    def _fmt_peso(self, val):
        try:
            return f"{float(val):.3f}"
        except Exception:
            return str(val)

    def _fmt_importe(self, val):
        try:
            return f"{float(val):.2f}".rstrip('0').rstrip('.')
        except Exception:
            return str(val)

    def on_exit(self):
        self.disconnect()
        self.destroy()

def main():
    app = App()
    app.mainloop()

if __name__ == "__main__":
    main()
