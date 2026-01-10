"use client"

import { API_CONFIG } from "@/lib/api-config"

type BridgeCtrl = {
  stop: () => Promise<void>
}

const baud = Number(process.env.NEXT_PUBLIC_SCALE_BAUD || "9600")
const minIntervalMs = Number(process.env.NEXT_PUBLIC_SCALE_MIN_INTERVAL_MS || "400")

export async function attachAutoScaleBridge(token: string, onData?: (data: unknown) => void): Promise<BridgeCtrl | null> {
  console.log("⚖️ [Balanza] Intentando conectar...");
  if (typeof navigator === "undefined" || !("serial" in navigator)) {
    console.error("❌ [Balanza] Web Serial API no soportada en este navegador.");
    return null;
  }

  const opened: { port: SerialPort; reader: ReadableStreamDefaultReader<string> }[] = []
  let lastSent = 0

  async function openPort(port: SerialPort) {
    console.log("🔌 [Balanza] Abriendo puerto serie...");
    try {
      await port.open({ baudRate: baud })
      console.log("✅ [Balanza] Puerto abierto correctamente.");
      const decoder = new TextDecoderStream()
      const reader = port.readable!.pipeThrough(decoder).getReader()
      opened.push({ port, reader })
        ; (async () => {
          let buffer = ""
          while (true) {
            try {
              const { value, done } = await reader.read()
              if (done) {
                console.log("🔌 [Balanza] Lectura finalizada (done).");
                break;
              }
              if (!value) continue
              console.log("📥 [Balanza] Datos crudos recibidos:", value);

              // Si tenemos callback, pasamos los datos crudos también para depuración
              if (onData) {
                // Intentamos pasar un objeto si parece JSON, o un objeto con "raw" si no
                try {
                  // Intento rápido de ver si es un JSON completo
                  if (value.trim().startsWith('{') && value.trim().endsWith('}')) {
                    // Dejamos que el bucle de abajo lo procese
                  } else {
                    // Si son datos parciales o texto plano, enviamos aviso
                    onData({ raw: value, timestamp: Date.now() });
                  }
                } catch {
                  onData({ raw: value, timestamp: Date.now() });
                }
              }

              buffer += value
              const parts = buffer.split(/\r?\n/)
              buffer = parts.pop() || ""
              for (const line of parts) {
                const now = Date.now()

                try {
                  // console.log("📝 [Balanza] Línea procesada:", line);
                  
                  // eslint-disable-next-line @typescript-eslint/no-explicit-any
                  let o: any = null;
                  try {
                    o = JSON.parse(line);
                  } catch {
                    // Si no es JSON, intentamos parsear buscando números (estilo monitor_peso_importe_v3.py)
                    // Buscamos números decimales (punto o coma)
                    const normalizedLine = line.replace(/,/g, ".");
                    // Regex para encontrar números: opcional signo, dígitos, opcional decimales
                    const matches = normalizedLine.match(/[-+]?\d+(?:\.\d+)?/g);
                    
                    if (matches && matches.length > 0) {
                      const peso = parseFloat(matches[0]);
                      // Si hay un segundo número, asumimos que es el precio/importe
                      const precio = matches.length >= 2 ? parseFloat(matches[1]) : undefined;
                      
                      o = { 
                        peso, 
                        precio, 
                        nombre: "Balanza" 
                      };
                    }
                  }

                  if (o) {
                    console.log("📦 [Balanza] Objeto procesado:", o);

                    // Callback para pruebas locales o visualización directa
                    if (onData) {
                      onData(o);
                    }

                    if (now - lastSent < minIntervalMs) continue

                    if (typeof o?.peso === "number") {
                      lastSent = now
                      console.log(`🚀 [Balanza] Enviando evento al backend (Peso: ${o.peso})`);
                      const body = {
                        peso: o.peso,
                        precio: typeof o?.precio === "number" ? o.precio : undefined,
                        nombre: typeof o?.nombre === "string" ? o.nombre : "Balanza",
                      }

                      // Si hay callback, asumimos modo prueba y podríamos querer evitar el POST, 
                      // pero por compatibilidad y para no romper lógica existente, lo mantenemos 
                      // a menos que explícitamente se quiera evitar.
                      // Por ahora, dejamos que siga enviando al backend.
                      await fetch(`${API_CONFIG.BASE_URL}/scanner/evento`, {
                        method: "POST",
                        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
                        body: JSON.stringify(body),
                      })
                    }
                  } else {
                     // Si no se pudo obtener un objeto válido (ni JSON ni regex)
                     console.warn("⚠️ [Balanza] No se pudo interpretar la línea:", line);
                     if (onData && line.trim().length > 0) {
                        onData({ rawLine: line, error: "Formato desconocido" });
                     }
                  }

                } catch (err) {
                   console.error("❌ [Balanza] Error inesperado procesando línea:", err);
                }
              }
            } catch (readError) {
              console.error("❌ [Balanza] Error leyendo del puerto:", readError);
              break;
            }
          }
        })()
    } catch (err) {
      console.error("❌ [Balanza] Error al abrir el puerto:", err);
    }
  }

  const ports = await navigator.serial.getPorts()
  for (const p of ports) await openPort(p)

  navigator.serial.addEventListener("connect", async (e: Event) => {
    const p = e.target as unknown as SerialPort
    await openPort(p)
  })

  navigator.serial.addEventListener("disconnect", async (e: Event) => {
    const p = e.target as unknown as SerialPort
    const idx = opened.findIndex(x => x.port === p)
    if (idx >= 0) {
      try {
        await opened[idx].reader.cancel()
      } catch { }
      try {
        await p.close()
      } catch { }
      opened.splice(idx, 1)
    }
  })

  return {
    stop: async () => {
      for (const { port, reader } of opened) {
        try {
          await reader.cancel()
        } catch { }
        try {
          await port.close()
        } catch { }
      }
      opened.splice(0, opened.length)
    },
  }
}
