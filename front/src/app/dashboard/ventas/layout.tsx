"use client"

import ProtectedRoute from "@/components/ProtectedRoute"

/* -------------------------------------------- PANEL VENTAS -------------------------------------------- */

export default function VentasLayout({ children }: { children: React.ReactNode }) {

  return ( 
    <ProtectedRoute allowedRoles={["admin", "cajero"]}>
      {children}
    </ProtectedRoute>
  )
}