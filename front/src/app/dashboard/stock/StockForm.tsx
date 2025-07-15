import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { 
    Select, 
    SelectTrigger, 
    SelectValue, 
    SelectContent, 
    SelectItem 
} from "@/components/ui/select"
import { useState } from "react";

/* Dependiendo el tipo de modo se crea o modifica un item */
type StockFormProps = {
  mode: "create" | "edit";
  initialData?: {
    id: string;
    nombre: string;
    cantidad: number;
    ubicacion: string;
    costoUnitario: number;
  };
};

export default function AddStockForm({ mode, initialData }: StockFormProps) {

  const [nombre, setNombre] = useState(initialData?.nombre || "");
  const [cantidad, setCantidad] = useState(initialData?.cantidad?.toString() || "");
  const [ubicacion, setUbicacion] = useState(initialData?.ubicacion || "");
  const [costo, setCosto] = useState(initialData?.costoUnitario?.toString() || "");

  const handleSubmit = (e: React.FormEvent) => {
      e.preventDefault();

      if (mode === "create") {
          
      // POST: Crear producto nuevo
      console.log("POST", { nombre, cantidad, ubicacion, costo });

      } else {

      // PATCH: Editar producto existente
      console.log("PATCH", {
          id: initialData?.id,
          nombre,
          cantidad,
          ubicacion,
          costo,
      });
      }
  };

  return (

    <form onSubmit={handleSubmit}>
      <div className="grid gap-6 py-4">
        <div className="grid grid-cols-4 items-center gap-4">
          <Label className="text-right">Nombre</Label>
          <Input value={nombre} onChange={(e) => setNombre(e.target.value)} placeholder="Jugo de Manzana" className="col-span-3" />
        </div>
        <div className="grid grid-cols-4 items-center gap-4">
          <Label className="text-right">Cantidad</Label>
          <Input value={cantidad} onChange={(e) => setCantidad(e.target.value)} placeholder="Ej: 10" className="col-span-3" />
        </div>
        <div className="grid grid-cols-4 items-center gap-4">
          <Label className="text-right">Ubicación</Label>
          <div className="col-span-3">
            <Select value={ubicacion} onValueChange={setUbicacion}>
              <SelectTrigger className="w-full">
                <SelectValue placeholder="Seleccionar ubicación" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="depositoA">Depósito A</SelectItem>
                <SelectItem value="depositoB">Depósito B</SelectItem>
                <SelectItem value="centro">Sucursal Centro</SelectItem>
                <SelectItem value="norte">Sucursal Norte</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
        <div className="grid grid-cols-4 items-center gap-4">
          <Label className="text-right">Costo Unitario</Label>
          <Input value={costo} onChange={(e) => setCosto(e.target.value)} placeholder="Ej: $1000" className="col-span-3" />
        </div>
      </div>
      <div className="flex justify-end mt-4">
        <Button type="submit" variant={mode === "create" ? "success" : "default"}>
          {mode === "create" ? "Agregar" : "Guardar Cambios"}
        </Button>
      </div>
    </form>
  );
}