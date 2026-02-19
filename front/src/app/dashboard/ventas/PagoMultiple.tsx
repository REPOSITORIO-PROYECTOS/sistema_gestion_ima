"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { X, Plus } from "lucide-react"

export interface Pago {
    id: string
    metodo_pago: string
    monto: number
}

interface PagoMultipleProps {
    pagos: Pago[]
    totalVenta: number
    onPagosChange: (pagos: Pago[]) => void
    onToggleMode: () => void
}

export function PagoMultiple({ pagos, totalVenta, onPagosChange, onToggleMode }: PagoMultipleProps) {
    const [nuevoMetodo, setNuevoMetodo] = useState("efectivo")
    const [nuevoMonto, setNuevoMonto] = useState("")
    const [mensajeDebug, setMensajeDebug] = useState("")

    const metodosDisponibles = [
        { value: "efectivo", label: "Efectivo" },
        { value: "transferencia", label: "Transferencia" },
        { value: "pos", label: "POS" },
    ]

    const sumaPagos = pagos.reduce((sum, p) => sum + p.monto, 0)
    const falta = Math.max(0, totalVenta - sumaPagos)
    const sobraOAjusta = sumaPagos !== totalVenta

    const handleAgregarPago = () => {
        console.log("handleAgregarPago llamado con nuevoMonto:", nuevoMonto)

        // Limpiar el input: remover espacios, puntos de millar, convertir coma a punto
        let valor = (nuevoMonto || "").trim()

        // Si viene vacío
        if (!valor) {
            setMensajeDebug("❌ Ingresa un monto")
            alert("⚠️ Por favor ingresa un monto")
            return
        }

        // Remover símbolo de pesos si existe
        valor = valor.replace(/[$\s]/g, "")

        // Quitar puntos de millar (pero solo si hay comas después)
        if (valor.includes(",")) {
            valor = valor.split(",")[0].replace(/\./g, "") + "," + valor.split(",")[1]
        }

        // Convertir coma a punto decimal
        valor = valor.replace(",", ".")

        const monto = parseFloat(valor)

        console.log("Valor procesado:", valor, "Monto parseado:", monto)

        // Validación
        if (isNaN(monto) || monto <= 0) {
            setMensajeDebug(`❌ Monto inválido: ${valor}`)
            alert("⚠️ Ingresa un monto válido mayor a $0")
            return
        }

        const nuevoPago: Pago = {
            id: `${Date.now()}-${Math.random()}`,
            metodo_pago: nuevoMetodo,
            monto: Math.round(monto * 100) / 100, // Redondear a 2 decimales
        }

        console.log("Agregando pago:", nuevoPago)
        setMensajeDebug(`✅ Pago de $${nuevoPago.monto.toFixed(2)} agregado`)
        setTimeout(() => setMensajeDebug(""), 2000)

        onPagosChange([...pagos, nuevoPago])
        setNuevoMonto("")
    }

    const handleEliminarPago = (idPago: string) => {
        onPagosChange(pagos.filter(p => p.id !== idPago))
    }

    const handleChangeMontoDir = (idPago: string, nuevoMonto: string) => {
        const montoParsed = parseFloat(nuevoMonto.replace(/\./g, "").replace(",", ".")) || 0
        onPagosChange(pagos.map(p => p.id === idPago ? { ...p, monto: montoParsed } : p))
    }

    return (
        <div className="flex flex-col gap-4 p-4 bg-green-100 rounded-lg mt-4 border-2 border-green-700">
            <div className="flex justify-between items-center">
                <div className="flex items-center gap-2">
                    <Label className="text-lg font-semibold text-green-900">Pagos Múltiples</Label>
                    <span className="bg-green-700 text-white rounded-full w-8 h-8 flex items-center justify-center font-bold text-sm">
                        {pagos.length}
                    </span>
                </div>
                <Button
                    variant="outline"
                    size="sm"
                    onClick={onToggleMode}
                    className="text-red-600 border-red-600"
                >
                    Cambiar a pago único
                </Button>
            </div>

            {/* Debug: Estado actual */}
            <div className="p-2 bg-blue-50 rounded border border-blue-200 text-xs text-blue-700 font-mono">
                📊 Pagos: {pagos.length} | Suma: ${sumaPagos.toFixed(2)} / ${totalVenta.toFixed(2)}
            </div>

            {/* Lista de pagos agregados */}
            {pagos.length > 0 && (
                <div className="space-y-2">
                    {pagos.map((pago) => (
                        <div
                            key={pago.id}
                            className="flex gap-2 items-center bg-white p-3 rounded border border-green-300"
                        >
                            <div className="flex-1">
                                <span className="font-semibold text-green-900">{pago.metodo_pago.toUpperCase()}</span>
                            </div>
                            <Input
                                type="text"
                                value={`$${pago.monto.toLocaleString("es-AR", {
                                    minimumFractionDigits: 2,
                                    maximumFractionDigits: 2,
                                })}`}
                                disabled
                                className="w-32 text-right font-bold"
                            />
                            <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => handleEliminarPago(pago.id)}
                                className="text-red-600 hover:bg-red-50"
                            >
                                <X className="w-4 h-4" />
                            </Button>
                        </div>
                    ))}
                </div>
            )}

            {/* Formulario para agregar nuevo pago */}
            <div className="flex flex-col gap-3 p-3 bg-green-50 rounded border border-green-300">
                <Label className="text-sm font-medium text-green-900">Agregar Método de Pago</Label>
                {mensajeDebug && (
                    <div className={`text-center text-sm font-semibold ${mensajeDebug.includes("✅") ? "text-green-700" : "text-red-700"}`}>
                        {mensajeDebug}
                    </div>
                )}
                <div className="flex gap-2 flex-col md:flex-row">
                    <Select value={nuevoMetodo} onValueChange={setNuevoMetodo}>
                        <SelectTrigger className="w-full md:w-40 cursor-pointer">
                            <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                            {metodosDisponibles.map((m) => (
                                <SelectItem key={m.value} value={m.value}>
                                    {m.label}
                                </SelectItem>
                            ))}
                        </SelectContent>
                    </Select>
                    <Input
                        type="text"
                        placeholder="Ej: 1000 o 1.000,50"
                        value={nuevoMonto}
                        onChange={(e) => setNuevoMonto(e.target.value)}
                        onKeyPress={(e) => {
                            if (e.key === 'Enter') {
                                handleAgregarPago()
                            }
                        }}
                        inputMode="decimal"
                        autoComplete="off"
                        className="flex-1 font-semibold"
                    />
                    <Button
                        onClick={handleAgregarPago}
                        className="bg-green-700 hover:bg-green-800 text-white"
                    >
                        <Plus className="w-4 h-4 mr-1" /> Agregar
                    </Button>
                </div>
            </div>

            {/* Resumen */}
            <div className="flex flex-col gap-2 p-3 bg-white rounded border border-green-300">
                <div className="flex justify-between items-center">
                    <span className="font-semibold">Total a pagar:</span>
                    <span className="font-bold text-lg">${totalVenta.toLocaleString("es-AR", { minimumFractionDigits: 2 })}</span>
                </div>
                <div className="flex justify-between items-center">
                    <span className="font-semibold">Suma de pagos:</span>
                    <span className={`font-bold text-lg ${sumaPagos > 0 ? (sobraOAjusta && Math.abs(sumaPagos - totalVenta) > 1 ? "text-red-600" : "text-green-600") : "text-gray-400"}`}>
                        ${sumaPagos.toLocaleString("es-AR", { minimumFractionDigits: 2 })}
                    </span>
                </div>
                <div className="h-0.5 bg-gray-200"></div>

                {falta > 0 && (
                    <div className="flex justify-between text-red-600">
                        <span className="font-semibold">🔴 Falta:</span>
                        <span className="font-bold">${falta.toLocaleString("es-AR", { minimumFractionDigits: 2 })}</span>
                    </div>
                )}

                {sumaPagos > totalVenta && (
                    <div className="flex justify-between text-blue-600">
                        <span className="font-semibold">🔵 Exceso:</span>
                        <span className="font-bold">
                            ${(sumaPagos - totalVenta).toLocaleString("es-AR", { minimumFractionDigits: 2 })}
                        </span>
                    </div>
                )}

                <div className={`text-center p-3 rounded font-bold text-sm ${sumaPagos === 0
                    ? "bg-gray-100 text-gray-700"
                    : Math.abs(sumaPagos - totalVenta) <= 1
                        ? "bg-green-200 text-green-900"
                        : "bg-yellow-200 text-yellow-900"
                    }`}>
                    {sumaPagos === 0 && "⚠️ Agrega al menos un pago"}
                    {sumaPagos > 0 && Math.abs(sumaPagos - totalVenta) <= 1 && "✅ Pago completo - Listo para procesar"}
                    {sumaPagos > 0 && Math.abs(sumaPagos - totalVenta) > 1 && `⚠️ Diferencia: $${Math.abs(sumaPagos - totalVenta).toFixed(2)}`}
                </div>
            </div>
        </div>
    )
}
