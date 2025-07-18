"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { Role, useAuthStore } from "@/lib/authStore"

interface Props {
  allowedRoles: Role[]
  children: React.ReactNode
}

export default function ProtectedRoute({ allowedRoles, children }: Props) {
  const router = useRouter()

  // Accedemos al rol desde Zustand
  const role = useAuthStore((state) => state.role)

  // Truco de hidratación: esperar a estar en el cliente
  const [isClient, setIsClient] = useState(false)
  useEffect(() => {
    setIsClient(true)
  }, [])

  useEffect(() => {
    if (!isClient) return

    console.log("🔐 [ProtectedRoute] Rol actual (cliente):", role)

    if (!role || !allowedRoles.includes(role)) {
      router.push("/")
    }
  }, [isClient, role, allowedRoles, router])

  if (!isClient || !role || !allowedRoles.includes(role)) {
    return (
      <div className="text-center py-4 text-muted-foreground">
        Verificando permisos...
      </div>
    )
  }

  return <>{children}</>
}