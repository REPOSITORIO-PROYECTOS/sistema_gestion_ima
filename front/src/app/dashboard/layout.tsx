"use client"

/* import Image from 'next/image' */
import NavBar from '@/components/interface/NavBar'
import ProtectedRoute from "@/components/ProtectedRoute"
import { useAuthStore } from '@/lib/authStore'

// Tipado de los path
type NavLink = {
  name: string
  href: string
  roles: string[]  // Roles permitidos
}

// Lista de secciones (paths) y sus roles permitidos - revisar si no va en ssr
const links: NavLink[] = [
  { name: "Ventas", href: "/dashboard/ventas", roles: ["Admin", "Cajero"] },
  { name: "Contabilidad", href: "/dashboard/contabilidad", roles: ["Admin", "Cajero"] },
  { name: "Stock", href: "/dashboard/stock", roles: ["Admin", "Cajero", "Gerente"] },
  { name: "Carta", href: "/dashboard/carta", roles: [""] }
]


function DashboardLayout({ children }: { children: React.ReactNode }) {

  // Global de Rol
  const role = useAuthStore(state => state.role) as string;

  return (
    
    // Al Dashboard inicial pueden acceder todos los roles
    <ProtectedRoute allowedRoles={["Admin", "Cajero", "Gerente"]}>
      
        {/* NavBar - los roles disablean */}
        <NavBar links={links} role={role} />

        {/* Frame principal de la App */}
        <main id="main-content" className="w-full min-h-screen py-32 px-8 relative">
          {children}   
        </main>

        {/* Copyright */}
        <footer className="text-center text-md text-gray-500 p-4">
          © 2019-{new Date().getFullYear()} Jugos Swing.
        </footer>

    </ProtectedRoute>
  );
}

export default DashboardLayout;