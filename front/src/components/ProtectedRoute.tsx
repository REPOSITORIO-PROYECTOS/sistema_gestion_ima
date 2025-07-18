"use client"

/* Este componente posee la lógica de admision y rutas basado en el rol del usuario */

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { useAuthStore } from "@/lib/authStore"

interface Props {
  allowedRoles: string[]      // permitimos uno o mas roles
  children: React.ReactNode
}

export default function ProtectedRoute({ allowedRoles, children }: Props) {
  const role = useAuthStore((state) => state.role)
  const hasHydrated = useAuthStore((state) => state.hasHydrated)
  const router = useRouter()
  const [isAuthorized, setIsAuthorized] = useState(false)

  useEffect(() => {
    
    if (!hasHydrated) return

    // Testeo de roles
    console.log("🔐 [ProtectedRoute] Rol actual:", role)

    if (role && allowedRoles.includes(role)) {
      setIsAuthorized(true)
    } else {
      router.push("/")
    }
  }, [hasHydrated, role, allowedRoles, router])

  if (!hasHydrated) return null
  if (!isAuthorized) return null

  return <>{children}</>
}