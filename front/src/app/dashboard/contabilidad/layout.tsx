import NavContabilidad from "@/components/interface/NavContabilidad";


const links = [
  
  { name: "Proveedores", href: "/dashboard/contabilidad/proveedores" },
  { name: "Clientes", href: "/dashboard/contabilidad/clientes" },
  { name: "Balance", href: "/dashboard/contabilidad/balance" },
];


function ContabilidadLayout({ children } : { children: React.ReactNode }) {

  return (
    <>
      <NavContabilidad links={links}/>

      <main className="w-full relative overflow-y-auto">

        <div className="sm:py-6 xl:py-8">
          {children}
        </div>

      </main>
    </>
  );
}

export default ContabilidadLayout;