"use client"

import { API_CONFIG } from "@/lib/api-config"

type BridgeCtrl = {
  stop: () => Promise<void>
}

const baud = Number(process.env.NEXT_PUBLIC_SCALE_BAUD || "9600")
const minIntervalMs = Number(process.env.NEXT_PUBLIC_SCALE_MIN_INTERVAL_MS || "400")

export async function attachAutoScaleBridge(token: string): Promise<BridgeCtrl | null> {
  if (typeof navigator === "undefined" || !("serial" in navigator)) return null
  const opened: { port: SerialPort; reader: ReadableStreamDefaultReader<string> }[] = []
  let lastSent = 0

  async function openPort(port: SerialPort) {
    try {
      await port.open({ baudRate: baud })
      const decoder = new TextDecoderStream()
      const reader = port.readable!.pipeThrough(decoder).getReader()
      opened.push({ port, reader })
      ;(async () => {
        let buffer = ""
        while (true) {
          const { value, done } = await reader.read()
          if (done) break
          if (!value) continue
          buffer += value
          const parts = buffer.split(/\r?\n/)
          buffer = parts.pop() || ""
          for (const line of parts) {
            const now = Date.now()
            if (now - lastSent < minIntervalMs) continue
            try {
              const o = JSON.parse(line)
              if (typeof o?.peso === "number") {
                lastSent = now
                const body = {
                  peso: o.peso,
                  precio: typeof o?.precio === "number" ? o.precio : undefined,
                  nombre: typeof o?.nombre === "string" ? o.nombre : "Balanza",
                }
                await fetch(`${API_CONFIG.BASE_URL}/scanner/evento`, {
                  method: "POST",
                  headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
                  body: JSON.stringify(body),
                })
              }
            } catch {}
          }
        }
      })()
    } catch {}
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
      } catch {}
      try {
        await p.close()
      } catch {}
      opened.splice(idx, 1)
    }
  })

  return {
    stop: async () => {
      for (const { port, reader } of opened) {
        try {
          await reader.cancel()
        } catch {}
        try {
          await port.close()
        } catch {}
      }
      opened.splice(0, opened.length)
    },
  }
}
