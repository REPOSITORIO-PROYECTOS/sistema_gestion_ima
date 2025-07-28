'use client';

import { useFacturacionStore } from '@/lib/facturacionStore';
import * as Switch from '@radix-ui/react-switch';

export default function GestionNegocio() {

  const { habilitarExtras, toggleExtras } = useFacturacionStore();

  return (
    <div className="flex flex-col gap-6 p-2">

      {/* Header */}
      <div className="space-y-2">
        <h2 className="text-3xl font-bold text-green-950">Gestión de Usuarios</h2>
        <p className="text-muted-foreground">Administrá los usuarios de tu aplicación.</p>
      </div>

      {/* Toggle de Facturación en Caja */}
      <div className="flex items-center gap-4">
        <h3 className="text-lg font-semibold text-green-950">
          Habilitar Remito / Presupuesto
        </h3>

        <Switch.Root
          checked={habilitarExtras}
          onCheckedChange={toggleExtras}
          className={`relative w-16 h-8 rounded-full ${
            habilitarExtras ? "bg-green-900" : "bg-gray-300"
          } cursor-pointer transition-colors`}
        >
          <Switch.Thumb
            className={`absolute top-1 left-1 w-6 h-6 bg-white rounded-full shadow-md transition-transform duration-300 ${
              habilitarExtras ? "translate-x-8" : "translate-x-0"
            }`}
          />
        </Switch.Root>
      </div>

    </div>
  );
}