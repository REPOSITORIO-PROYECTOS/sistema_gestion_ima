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

type StockFormProps = {
  mode: "create" | "edit";
  initialData?: {
    id: number;
    descripcion: string;
    stock_actual: number;
    ubicacion?: string;
    precio_venta: number;
  };
};

export default function AddStockForm({ mode, initialData }: StockFormProps) {
  const [descripcion, setDescripcion] = useState(initialData?.descripcion || "");
  const [stock, setStock] = useState(initialData?.stock_actual?.toString() || "");
  const [ubicacion, setUbicacion] = useState(initialData?.ubicacion || "");
  const [precioVenta, setPrecioVenta] = useState(initialData?.precio_venta?.toString() || "");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    if (mode === "create") {
      console.log("POST", { descripcion, stock, ubicacion, precioVenta });
    } else {
      console.log("PATCH", {
        id: initialData?.id,
        descripcion,
        stock,
        ubicacion,
        precioVenta,
      });
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <div className="grid gap-6 py-4">
        <div className="grid grid-cols-4 items-center gap-4">
          <Label className="text-right">Nombre</Label>
          <Input value={descripcion} onChange={(e) => setDescripcion(e.target.value)} placeholder="Jugo de Manzana" className="col-span-3" />
        </div>
        <div className="grid grid-cols-4 items-center gap-4">
          <Label className="text-right">Stock</Label>
          <Input value={stock} onChange={(e) => setStock(e.target.value)} placeholder="Ej: 10" className="col-span-3" />
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
          <Label className="text-right">Precio Venta</Label>
          <Input value={precioVenta} onChange={(e) => setPrecioVenta(e.target.value)} placeholder="Ej: $1000" className="col-span-3" />
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