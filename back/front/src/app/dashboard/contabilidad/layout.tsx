import NavContabilidad from "@/components/interface/NavContabilidad";
import ProtectedRoute from "@/components/ProtectedRoute";

const links = [
  
  { name: "Movimientos", href: "/dashboard/contabilidad" },
  { name: "Proveedores", href: "/dashboard/contabilidad/proveedores" },
  { name: "Clientes", href: "/dashboard/contabilidad/clientes" },
  { name: "Arqueo de Caja", href: "/dashboard/contabilidad/arqueo" },
];

function ContabilidadLayout({ children } : { children: React.ReactNode }) {

  return (

    <ProtectedRoute allowedRoles={["Admin", "Cajero"]}>

      <div className="flex flex-col lg:flex-row w-full items-center lg:justify-between gap-4">
        <h2 className="text-3xl font-semibold">Sección de Contabilidad</h2>

        {/* Nav de Contabilidad */}
        <NavContabilidad links={links}/>
      </div>
      
      
      {/* Subsección de Contabilidad */}
      <main className="w-full relative overflow-y-auto">

        <div className="sm:py-6 xl:py-8">
          {children}
        </div>

      </main>
    </ProtectedRoute>

  );
}

export default ContabilidadLayout;