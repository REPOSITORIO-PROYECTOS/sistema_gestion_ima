"use client"

/* Este componente posee la lógica de admision y rutas basado en el rol del usuario */

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { Role, useAuthStore } from "@/lib/authStore"

interface Props {
  allowedRoles: Role[]
  children: React.ReactNode
}

export default function ProtectedRoute({ allowedRoles, children }: Props) {

  const role = useAuthStore((state) => state.role)
  const hasHydrated = useAuthStore((state) => state.hasHydrated)
  const router = useRouter()
  const [isAuthorized, setIsAuthorized] = useState(false)

  useEffect(() => {

    if (!hasHydrated) return

    console.log("🔐 [ProtectedRoute] Rol actual:", role)

    if (role && allowedRoles.includes(role)) {
      setIsAuthorized(true)
    } else {
      setIsAuthorized(false)
      router.push("/")
    }
  }, [hasHydrated, role, allowedRoles, router])

  console.log("🧪 Estado completo:", {
    hydrated: hasHydrated,
    role,
  })

  if (!hasHydrated || !isAuthorized) {
    return (
      <div className="text-center py-4 text-muted-foreground">
        Verificando permisos...
      </div>
    )
  }

  return <>{children}</>
}