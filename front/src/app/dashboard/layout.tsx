"use client"

import Image from 'next/image'
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
  { name: "Ventas", href: "/dashboard/ventas", roles: ["admin", "cajero"] },
  { name: "Contabilidad", href: "/dashboard/contabilidad", roles: ["admin", "contable"] },
  { name: "Stock", href: "/dashboard/stock", roles: ["admin", "contable"] },
  { name: "Carta", href: "/dashboard/carta", roles: ["admin"] }
]


function DashboardLayout({ children }: { children: React.ReactNode }) {

  // Global de Rol
  const role = useAuthStore(state => state.role) as string;

  return (
    
    // Al Dashboard inicial pueden acceder todos los roles
    <ProtectedRoute allowedRoles={["admin", "cajero", "contable"]}>
      
        {/* Header */}
        <header className="bg-green-700 border-b border-gray-200 fixed z-30 w-full" aria-label='Banner Nav'>
          <div className="px-3 py-3 lg:px-5 lg:pl-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center justify-start">

                {/* Logo */}
                <a href="/dashboard" className="text-xl font-bold flex items-center gap-2 lg:ml-2.5">
                  <Image src="/logo.png" alt="Swing Jugos" width={50} height={50} />
                  <span className="hidden self-center whitespace-nowrap ml-2 italic text-white sm:block">
                    Sistema{" "}Gestion{" "}Jugos{" "}Swing
                  </span>
                </a>

              </div>

              {/* User Avatar */} 
              <div className="flex items-center">
                <div className="bg-green-300 text-gray-800 font-semibold p-2 rounded-full w-12 h-12 flex items-center justify-center">IM</div>
              </div>

            </div>
          </div>
        </header>


        {/* NavBar de las secciones / Se pasan roles como prop para disablear secciones */}
        <NavBar links={links} role={role} />


        {/* Frame principal de la App */}
        <main id="main-content" className="w-full pt-36 pb-12 bg-white relative overflow-y-auto">
          <div className="pt-2 px-1">
            <div className="w-full min-h-[calc(100vh-230px)]">
              <div className="bg-white shadow rounded-lg p-4 sm:p-5">
                {children}
              </div>
            </div>
          </div>
        </main>


        {/* Copyright y Fecha */}
        <p className="text-center text-sm text-gray-500 mb-10">&copy; 2019-{new Date().getFullYear()}{" "}Jugos Swing.</p>
    
    </ProtectedRoute>
  );
}

export default DashboardLayout;