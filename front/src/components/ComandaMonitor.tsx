
'use client'

import { useEffect, useState } from 'react';
import { api } from '@/lib/api-client';
import { useAuthStore } from '@/lib/authStore';
import { toast } from 'sonner';
import { buildTicketHtml, printHtml } from '@/lib/printerService';
import { Printer, Settings } from 'lucide-react';
import { Button } from './ui/button';

interface ComandaMonitorProps {
  autoPrint?: boolean;
}

export default function ComandaMonitor() {
  const [active, setActive] = useState(false);
  const [lastCheck, setLastCheck] = useState<Date | null>(null);
  const [showConfig, setShowConfig] = useState(false);
  const [monitorRoles, setMonitorRoles] = useState<{ cocina: boolean, bar: boolean }>({ cocina: true, bar: true });
  const token = useAuthStore((state) => state.token);
  const isCaja = true; // Assuming this component is only mounted/enabled on Caja/Main PC

  // Load state from local storage
  useEffect(() => {
    const saved = localStorage.getItem('comandaMonitorActive');
    if (saved) {
      setActive(saved === 'true');
    }
    const savedRoles = localStorage.getItem('comandaMonitorRoles');
    if (savedRoles) {
      try {
        setMonitorRoles(JSON.parse(savedRoles));
      } catch (e) {
        console.error("Error parsing saved roles", e);
      }
    }
  }, []);

  const toggleActive = () => {
    const newState = !active;
    setActive(newState);
    localStorage.setItem('comandaMonitorActive', String(newState));
    if (newState) {
      toast.success("Monitor de Comandas Activado");
    } else {
      toast.info("Monitor de Comandas Desactivado");
    }
  };

  const toggleRole = (role: 'cocina' | 'bar') => {
    const newRoles = { ...monitorRoles, [role]: !monitorRoles[role] };
    setMonitorRoles(newRoles);
    localStorage.setItem('comandaMonitorRoles', JSON.stringify(newRoles));
  };

  useEffect(() => {
    if (!active || !token) return;

    const checkComandas = async () => {
      try {
        const res = await api.comandas.getPendientes();
        if (res.success && Array.isArray(res.data) && res.data.length > 0) {
          const detalles = res.data;
          console.log("Comandas pendientes encontradas:", detalles.length);

          // Agrupar por Mesa
          const porMesa: Record<number, typeof detalles> = {};
          detalles.forEach(d => {
            // @ts-ignore - mesa object might be nested or we need to rely on id_mesa
            const mesaId = d.id_mesa || d.consumo?.id_mesa;
            if (!porMesa[mesaId]) porMesa[mesaId] = [];
            porMesa[mesaId].push(d);
          });

          const idsToMark: number[] = [];

          // Procesar cada mesa
          for (const [mesaId, items] of Object.entries(porMesa)) {
            // Separar Cocina y Bar
            const esDeBar = (cat: string, desc: string) => {
              const text = `${(cat || '').toLowerCase()} ${(desc || '').toLowerCase()}`;
              return /bebida|trago|bar|vino|cerveza|gaseosa|agua/.test(text);
            };

            const cocina = items.filter(d => !esDeBar(d.articulo?.categoria?.nombre, d.articulo?.descripcion));
            const bar = items.filter(d => esDeBar(d.articulo?.categoria?.nombre, d.articulo?.descripcion));

            // Helper para imprimir
            const imprimirGrupo = (grupo: typeof items, titulo: string) => {
              if (grupo.length === 0) return;

              // Construir objeto pseudo-ticket para reutilizar printerService
              const mesaNum = grupo[0].consumo?.mesa?.numero || '?';
              const ticketData: any = {
                mesa_numero: mesaNum,
                timestamp: new Date().toISOString(),
                detalles: grupo.map(d => ({
                  articulo: d.articulo?.descripcion || 'Item',
                  cantidad: d.cantidad,
                  precio_unitario: d.precio_unitario,
                  subtotal: d.cantidad * d.precio_unitario,
                  categoria: d.articulo?.categoria?.nombre,
                  observacion: d.observacion // Incluir observación
                })),
                total: 0 // No importa para comanda
              };

              const html = buildTicketHtml(titulo, ticketData);
              printHtml(html);
            };

            if (monitorRoles.cocina && cocina.length > 0) imprimirGrupo(cocina, 'COMANDA COCINA');
            if (monitorRoles.bar && bar.length > 0) imprimirGrupo(bar, 'COMANDA BAR');
          }

          // Marcar como impresos
          const ids = detalles.map(d => d.id);
          await api.comandas.marcarImpreso(ids);
          toast.success(`${detalles.length} items enviados a cocina/bar`);
        }
        setLastCheck(new Date());
      } catch (error) {
        console.error("Error checking comandas:", error);
      }
    };

    // Check immediately
    checkComandas();

    // Then every 10 seconds
    const interval = setInterval(checkComandas, 10000);
    return () => clearInterval(interval);

  }, [active, token, monitorRoles]);

  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col items-end gap-2">
      {showConfig && (
        <div className="bg-white p-4 rounded-lg shadow-xl border mb-2 w-48 animate-in slide-in-from-bottom-5">
          <h4 className="font-semibold mb-2 text-sm">Configuración Monitor</h4>
          <div className="space-y-2">
            <label className="flex items-center space-x-2 text-sm cursor-pointer">
              <input
                type="checkbox"
                checked={monitorRoles.cocina}
                onChange={() => toggleRole('cocina')}
                className="rounded border-gray-300"
              />
              <span>Imprimir Cocina</span>
            </label>
            <label className="flex items-center space-x-2 text-sm cursor-pointer">
              <input
                type="checkbox"
                checked={monitorRoles.bar}
                onChange={() => toggleRole('bar')}
                className="rounded border-gray-300"
              />
              <span>Imprimir Bar</span>
            </label>
          </div>
        </div>
      )}
      <div className="flex gap-2">
        <Button
          onClick={() => setShowConfig(!showConfig)}
          variant="secondary"
          size="sm"
          className="shadow-lg border bg-white"
        >
          <Settings className="w-4 h-4" />
        </Button>
        <Button
          onClick={toggleActive}
          variant={active ? "default" : "secondary"}
          className={`shadow-lg border ${active ? 'bg-green-600 hover:bg-green-700' : 'bg-gray-200'}`}
          size="sm"
        >
          <Printer className={`w-4 h-4 mr-2 ${active ? 'animate-pulse' : ''}`} />
          {active ? 'Monitor Activo' : 'Monitor Inactivo'}
        </Button>
      </div>
    </div>
  );
}
