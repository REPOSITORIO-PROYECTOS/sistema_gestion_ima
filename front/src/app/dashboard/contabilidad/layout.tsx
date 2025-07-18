import NavContabilidad from "@/components/interface/NavContabilidad";
import ProtectedRoute from "@/components/ProtectedRoute";

const links = [
  
  { name: "Proveedores", href: "/dashboard/contabilidad/proveedores" },
  { name: "Clientes", href: "/dashboard/contabilidad/clientes" },
  { name: "Balance", href: "/dashboard/contabilidad/balance" },
];

function ContabilidadLayout({ children } : { children: React.ReactNode }) {

  return (

    <ProtectedRoute allowedRoles={["Admin", "Cajero"]}>

      {/* Nav de Contabilidad */}
      <NavContabilidad links={links}/>
      
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