"use client";

import { useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import ExcelUploader from "./ExcelUploader";
import { Proveedor } from "../proveedores/columns";

interface Props {
  proveedor: Proveedor;
}

export const ProveedorExcelUpload: React.FC<Props> = ({ proveedor }) => {
  const [open, setOpen] = useState(false);

  const handleFileUpload = (file: File) => {
    console.log(`Archivo subido para el proveedor: ${proveedor.nombre_razon_social}`);
    console.log(file);

    // Acá podés hacer un fetch al backend:
    /*
    const formData = new FormData();
    formData.append("file", file);
    formData.append("proveedor", proveedor.nombre_razon_social);
    await fetch('/api/upload-excel', {
      method: "POST",
      body: formData,
    });
    */

    setOpen(false); // cerrar el modal
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm">📄 Cargar Excel</Button>
      </DialogTrigger>

      <DialogContent>
        <DialogHeader>
          <DialogTitle>Cargar Excel para {proveedor.nombre_razon_social}</DialogTitle>
        </DialogHeader>
        <ExcelUploader onFileSelect={handleFileUpload} />
      </DialogContent>
    </Dialog>
  );
};