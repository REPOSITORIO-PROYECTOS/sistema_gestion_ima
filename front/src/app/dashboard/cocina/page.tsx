
"use client"

import { useEffect, useState } from "react"
import { api as apiClient } from "@/lib/api-client"
import { ConsumoMesaDetallePopulated } from "@/lib/types/mesas"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Clock, UtensilsCrossed, CheckCircle2, ChefHat, ArrowRight } from "lucide-react"
import { toast } from "sonner"
import { formatDistanceToNow } from "date-fns"
import { es } from "date-fns/locale"

export default function CocinaPage() {
  const [items, setItems] = useState<ConsumoMesaDetallePopulated[]>([])
  const [loading, setLoading] = useState(true)
  const [lastUpdated, setLastUpdated] = useState<Date>(new Date())

  const fetchItems = async (silent = false) => {
    try {
      if (!silent) setLoading(true)
      const res = await apiClient.cocina.getItems()
      if (res.success && res.data) {
        setItems(res.data)
        setLastUpdated(new Date())
      }
    } catch (error) {
      console.error("Error fetching items:", error)
      if (!silent) toast.error("Error al cargar pedidos de cocina")
    } finally {
      if (!silent) setLoading(false)
    }
  }

  useEffect(() => {
    fetchItems()
    // Polling cada 10 segundos
    const interval = setInterval(() => fetchItems(true), 10000)
    return () => clearInterval(interval)
  }, [])

  const handleEstadoChange = async (id: number, nuevoEstado: string) => {
    try {
      // Optimistic update
      setItems(prev => prev.map(item =>
        item.id === id ? { ...item, estado_cocina: nuevoEstado as any } : item
      ))

      const res = await apiClient.cocina.updateEstado(id, nuevoEstado)
      if (res.success) {
        toast.success(`Estado actualizado a ${nuevoEstado}`)
        fetchItems(true) // Refresh to ensure sync
      } else {
        throw new Error("Failed to update")
      }
    } catch (error) {
      console.error(error)
      toast.error("Error al actualizar estado")
      fetchItems(true) // Revert on error
    }
  }

  // Agrupar items por estado
  const pendientes = items.filter(i => !i.estado_cocina || i.estado_cocina === "PENDIENTE")
  const enPreparacion = items.filter(i => i.estado_cocina === "EN_PREPARACION")
  const listos = items.filter(i => i.estado_cocina === "LISTO")

  const TicketCard = ({ item }: { item: ConsumoMesaDetallePopulated }) => {
    const isLate = false // TODO: Implementar lógica de tiempo

    return (
      <Card className="mb-3 overflow-hidden border-l-4 border-l-primary">
        <CardContent className="p-4">
          <div className="flex justify-between items-start mb-2">
            <div>
              <div className="font-bold text-lg flex items-center gap-2">
                <span className="bg-primary/10 text-primary px-2 py-0.5 rounded text-sm">
                  Mesa {item.consumo?.mesa?.numero || "?"}
                </span>
                <span className="text-muted-foreground text-xs">
                  #{item.id}
                </span>
              </div>
              <h3 className="font-semibold text-lg mt-1">
                {item.cantidad}x {item.articulo?.descripcion}
              </h3>
              {item.observacion && (
                <div className="mt-2 bg-yellow-50 text-yellow-800 p-2 rounded text-sm border border-yellow-200">
                  📝 {item.observacion}
                </div>
              )}
            </div>
            {/* <div className="text-xs text-muted-foreground flex items-center gap-1">
              <Clock className="w-3 h-3" />
               Hace 5m
            </div> */}
          </div>

          <div className="flex justify-end gap-2 mt-4 pt-2 border-t">
            {(!item.estado_cocina || item.estado_cocina === "PENDIENTE") && (
              <Button
                size="sm"
                onClick={() => handleEstadoChange(item.id, "EN_PREPARACION")}
                className="bg-blue-600 hover:bg-blue-700"
              >
                <ChefHat className="w-4 h-4 mr-1" />
                Preparar
              </Button>
            )}

            {item.estado_cocina === "EN_PREPARACION" && (
              <>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => handleEstadoChange(item.id, "PENDIENTE")}
                >
                  Volver
                </Button>
                <Button
                  size="sm"
                  onClick={() => handleEstadoChange(item.id, "LISTO")}
                  className="bg-green-600 hover:bg-green-700"
                >
                  <CheckCircle2 className="w-4 h-4 mr-1" />
                  Listo
                </Button>
              </>
            )}

            {item.estado_cocina === "LISTO" && (
              <Button
                size="sm"
                variant="secondary"
                onClick={() => handleEstadoChange(item.id, "ENTREGADO")}
              >
                <ArrowRight className="w-4 h-4 mr-1" />
                Entregar
              </Button>
            )}
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="h-full flex flex-col">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2">
            <UtensilsCrossed className="w-8 h-8" />
            Cocina / Monitor de Pedidos
          </h1>
          <p className="text-muted-foreground">
            Última actualización: {lastUpdated.toLocaleTimeString()}
          </p>
        </div>
        <Button onClick={() => fetchItems()} variant="outline">
          Actualizar Ahora
        </Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 h-full min-h-[500px]">
        {/* Columna Pendientes */}
        <div className="bg-gray-50/50 rounded-xl p-4 border border-dashed">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-xl text-gray-700 flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-red-500" />
              Pendientes
            </h2>
            <Badge variant="secondary">{pendientes.length}</Badge>
          </div>
          <div className="space-y-3">
            {pendientes.length === 0 && <p className="text-center text-gray-400 py-8">No hay pedidos pendientes</p>}
            {pendientes.map(item => (
              <TicketCard key={item.id} item={item} />
            ))}
          </div>
        </div>

        {/* Columna En Preparación */}
        <div className="bg-blue-50/30 rounded-xl p-4 border border-blue-100">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-xl text-blue-700 flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-blue-500" />
              En Preparación
            </h2>
            <Badge variant="secondary" className="bg-blue-100 text-blue-700">{enPreparacion.length}</Badge>
          </div>
          <div className="space-y-3">
            {enPreparacion.length === 0 && <p className="text-center text-gray-400 py-8">Nada en preparación</p>}
            {enPreparacion.map(item => (
              <TicketCard key={item.id} item={item} />
            ))}
          </div>
        </div>

        {/* Columna Listos */}
        <div className="bg-green-50/30 rounded-xl p-4 border border-green-100">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-xl text-green-700 flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-green-500" />
              Listos para Servir
            </h2>
            <Badge variant="secondary" className="bg-green-100 text-green-700">{listos.length}</Badge>
          </div>
          <div className="space-y-3">
            {listos.length === 0 && <p className="text-center text-gray-400 py-8">Nada listo</p>}
            {listos.map(item => (
              <TicketCard key={item.id} item={item} />
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
