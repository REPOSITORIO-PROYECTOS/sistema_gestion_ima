"use client"

import NavBar from '@/components/interface/NavBar'
import ProtectedRoute from "@/components/ProtectedRoute"
import { useAuthStore } from '@/lib/authStore'
import ComandaMonitor from '@/components/ComandaMonitor'

// Tipado de los path
type NavLink = {
  name: string
  href: string
  roles: string[]  // Roles permitidos
}

// Lista de secciones (paths) y sus roles permitidos - revisar si no va en ssr
const links: NavLink[] = [
  { name: "Ventas", href: "/dashboard/ventas", roles: ["Admin", "Cajero","Gerente"] },
  { name: "Mesas", href: "/dashboard/mesas", roles: ["Admin", "Cajero","Gerente"] },
  { name: "Contabilidad", href: "/dashboard/contabilidad", roles: ["Admin","Gerente"] },
  { name: "Stock", href: "/dashboard/stock", roles: ["Admin","Gerente"] },
]

function DashboardLayout({ children }: { children: React.ReactNode }) {

  // Global de Rol
  const role = useAuthStore(state => state.role)

  return (
    
    // Al Dashboard inicial pueden acceder todos los roles
    <ProtectedRoute allowedRoles={["Admin", "Cajero", "Gerente"]}>
      
      {/* NavBar - los roles disablean */}
      <NavBar links={links} role={role?.nombre ?? ""} />

      {/* Frame principal de la App */}
      <main id="main-content" className="w-full min-h-screen py-32 px-8 relative">
        {children}   
      </main>

      {/* Monitor de Comandas (Solo visible si se activa manualmente) */}
      {(role?.nombre === 'Admin' || role?.nombre === 'Cajero') && <ComandaMonitor />}

      {/* Copyright */}
      <footer className="text-center text-md text-gray-500 p-4">
        © 2019-{new Date().getFullYear()} IMA Consultoría.
      </footer>

    </ProtectedRoute>
  );
}

export default DashboardLayout;