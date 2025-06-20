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

// Lista de secciones (paths) y sus roles permitidos
const links: NavLink[] = [
  { name: "Ventas", href: "/dashboard/ventas", roles: ["admin", "cajero"] },
  { name: "Contabilidad", href: "/dashboard/contabilidad", roles: ["admin", "contable"] },
  { name: "Stock", href: "/dashboard/stock", roles: ["admin", "contable"] },
]


function DashboardLayout({ children }: { children: React.ReactNode }) {

  // Global de Rol
  const role = useAuthStore(state => state.role) as string;

  return (
    
    // Al Dashboard inicial pueden acceder todos los roles
    <ProtectedRoute allowedRoles={["admin", "cajero", "contable"]}>
      <>
        {/* Header */}
        <nav className="bg-green-700 border-b border-gray-200 fixed z-30 w-full" aria-label='Banner Nav'>
          <div className="px-3 py-3 lg:px-5 lg:pl-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center justify-start">

                <button id="toggleSidebarMobile" aria-expanded="true" aria-controls="sidebar"
                className="lg:hidden mr-2 text-gray-600 hover:text-gray-900 cursor-pointer p-2 hover:bg-gray-100 focus:bg-gray-100 focus:ring-2 focus:ring-gray-100 rounded">
                  
                  <svg id="toggleSidebarMobileHamburger" className="w-6 h-6" fill="currentColor" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg">
                    <path fillRule="evenodd" d="M3 5a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zM3 10a1 1 0 011-1h6a1 1 0 110 2H4a1 1 0 01-1-1zM3 15a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1z" clipRule="evenodd"></path>
                  </svg>

                  <svg id="toggleSidebarMobileClose" className="w-6 h-6 hidden" fill="currentColor" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg">
                    <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd"></path>
                  </svg>
                  
                </button>

                {/* Logo */}
                <a href="/dashboard" className="text-xl font-bold flex items-center gap-2 lg:ml-2.5">
                  <Image src="/logo.png" alt="Swing Jugos" width={50} height={50} />
                  <span className="self-center whitespace-nowrap ml-2 italic text-white">
                    Sistema{" "}Gestion{" "}Jugo{" "}Swing
                  </span>
                </a>

              </div>

              {/* User Avatar */} 
              <div className="flex items-center">
                <div className="bg-green-300 text-gray-800 font-semibold p-2 rounded-full w-12 h-12 flex items-center justify-center">IM</div>
              </div>

            </div>
          </div>
        </nav>


        {/* NavBar de las secciones / Se pasa el rol para permitir o deshabilitar links y secciones en base al rol */}
        <NavBar links={links} role={role} />


        {/* Frame principal de la App / Aca se renderizan todas las subsecciones */}
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
      </>
    </ProtectedRoute>
  );
}

export default DashboardLayout;