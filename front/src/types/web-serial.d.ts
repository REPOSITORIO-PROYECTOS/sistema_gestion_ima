"use client"

declare interface SerialPort {
  open(options: { baudRate: number }): Promise<void>
  readable?: ReadableStream
  close(): Promise<void>
}

interface Navigator {
  serial: {
    getPorts(): Promise<SerialPort[]>
    addEventListener(
      type: "connect" | "disconnect",
      listener: (e: Event) => void
    ): void
  }
}
