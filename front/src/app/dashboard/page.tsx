"use client"

import { useEmpresaStore } from "@/lib/empresaStore";

export default function Inicio() {

  const empresa = useEmpresaStore((state) => state.empresa);
  console.log(empresa)

  return (

    /* Página Bienvenida */
    <div className="flex flex-col items-center gap-4">

      <h1 className="flex flex-col justify-center items-center md:top-46 relative text-3xl font-bold text-green-950">
        {`Sistema de Gestión - ${empresa?.nombre_negocio}`}
      </h1>

    </div>
  );
}