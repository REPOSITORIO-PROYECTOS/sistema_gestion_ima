"use client"

import NavBar from '@/components/interface/NavBar'
import ProtectedRoute from "@/components/ProtectedRoute"
import { useAuthStore } from '@/lib/authStore'
import ComandaMonitor from '@/components/ComandaMonitor'
import { usePathname } from 'next/navigation'

// Tipado de los path
type NavLink = {
  name: string
  href: string
  roles: string[]  // Roles permitidos
}

// Lista de secciones (paths) y sus roles permitidos - revisar si no va en ssr
const links: NavLink[] = [
  { name: "Ventas", href: "/dashboard/ventas", roles: ["Admin", "Cajero", "Vendedora", "Gerente", "Encargada"] },
  { name: "Mesas", href: "/dashboard/mesas", roles: ["Admin", "Cajero", "Vendedora", "Gerente", "Encargada"] },
  { name: "Cocina", href: "/dashboard/cocina", roles: ["Admin", "Cajero", "Vendedora", "Gerente", "Encargada"] },
  { name: "Estadísticas", href: "/dashboard/estadisticas", roles: ["Admin", "Gerente", "Encargada", "Soporte"] },
  { name: "Contabilidad", href: "/dashboard/contabilidad", roles: ["Admin", "Gerente", "Encargada"] },
  { name: "Stock", href: "/dashboard/stock", roles: ["Admin", "Gerente", "Encargada"] },
]

function DashboardLayout({ children }: { children: React.ReactNode }) {

  // Global de Rol
  const role = useAuthStore(state => state.role)
  const pathname = usePathname()

  return (

    // Al Dashboard inicial pueden acceder todos los roles
    <ProtectedRoute allowedRoles={["Admin", "Cajero", "Vendedora", "Gerente", "Encargada"]}>

      {/* NavBar - los roles disablean */}
      <NavBar links={links} role={role?.nombre ?? ""} />

      {/* Frame principal de la App */}
      <main id="main-content" className="w-full min-h-screen py-32 px-8 relative">
        {children}
      </main>

      {/* Monitor de Comandas (Solo visible si se activa manualmente y estamos en Mesas) */}
      {(role?.nombre === 'Admin' || role?.nombre === 'Cajero' || role?.nombre === 'Vendedora') && pathname === '/dashboard/mesas' && <ComandaMonitor />}

      {/* Copyright */}
      <footer className="text-center text-md text-gray-500 p-4">
        © 2019-{new Date().getFullYear()} IMA Consultoría.
      </footer>

    </ProtectedRoute>
  );
}

export default DashboardLayout;