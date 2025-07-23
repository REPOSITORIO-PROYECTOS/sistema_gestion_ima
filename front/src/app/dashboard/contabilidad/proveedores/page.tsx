"use client";

import { useState } from "react";
import { DataTable } from "./data-table";
import { columns } from "./columns";
import { ProductosProveedor } from "./columns";

function Proveedores() {
  const [data, setData] = useState<ProductosProveedor[]>([]);

  const handleFileUpload = async (file: File) => {
    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch("https://tuservidor/api/endpoint", {
        method: "POST",
        body: formData,
      });

      if (!res.ok) throw new Error("Error en el backend");

      const parsedData = await res.json();
      setData(parsedData); 
    } catch (err) {
      console.error(err);
      alert("Hubo un error al subir el archivo.");
    }
  };

  return (
    <div>
      <DataTable
        columns={columns}
        data={data}
        onFileUpload={handleFileUpload} 
      />
    </div>
  );
}

export default Proveedores;