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

    const metodosDisponibles = [
        { value: "efectivo", label: "Efectivo" },
        { value: "transferencia", label: "Transferencia" },
        { value: "pos", label: "POS" },
    ]

    const sumaPagos = pagos.reduce((sum, p) => sum + p.monto, 0)
    const falta = Math.max(0, totalVenta - sumaPagos)
    const sobraOAjusta = sumaPagos !== totalVenta

    const handleAgregarPago = () => {
        const monto = parseFloat(nuevoMonto.replace(/\./g, "").replace(",", ".")) || 0
        if (monto <= 0) {
            alert("Ingresa un monto válido")
            return
        }

        const nuevoPago: Pago = {
            id: `${Date.now()}-${Math.random()}`,
            metodo_pago: nuevoMetodo,
            monto: monto,
        }
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
                <Label className="text-lg font-semibold text-green-900">Pagos Múltiples</Label>
                <Button
                    variant="outline"
                    size="sm"
                    onClick={onToggleMode}
                    className="text-red-600 border-red-600"
                >
                    Cambiar a pago único
                </Button>
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
                        placeholder="Monto ($)"
                        value={nuevoMonto}
                        onChange={(e) => setNuevoMonto(e.target.value)}
                        inputMode="decimal"
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
                <div className="flex justify-between">
                    <span className="font-semibold">Total a pagar:</span>
                    <span className="font-bold">${totalVenta.toLocaleString("es-AR", { minimumFractionDigits: 2 })}</span>
                </div>
                <div className="flex justify-between">
                    <span className="font-semibold">Suma de pagos:</span>
                    <span className={`font-bold ${sobraOAjusta ? "text-red-600" : "text-green-600"}`}>
                        ${sumaPagos.toLocaleString("es-AR", { minimumFractionDigits: 2 })}
                    </span>
                </div>

                {falta > 0 && (
                    <div className="flex justify-between text-red-600">
                        <span className="font-semibold">Falta:</span>
                        <span className="font-bold">${falta.toLocaleString("es-AR", { minimumFractionDigits: 2 })}</span>
                    </div>
                )}

                {sumaPagos > totalVenta && (
                    <div className="flex justify-between text-blue-600">
                        <span className="font-semibold">Exceso:</span>
                        <span className="font-bold">
                            ${(sumaPagos - totalVenta).toLocaleString("es-AR", { minimumFractionDigits: 2 })}
                        </span>
                    </div>
                )}

                <div className={`text-center p-2 rounded font-bold ${sumaPagos === totalVenta ? "bg-green-200 text-green-900" : "bg-yellow-200 text-yellow-900"}`}>
                    {sumaPagos === totalVenta ? "✓ Pago completo" : "Ajusta los montos para completar"}
                </div>
            </div>
        </div>
    )
}
