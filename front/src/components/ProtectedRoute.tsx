"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { Role, useAuthStore } from "@/lib/authStore"

interface Props {
  allowedRoles: Role["nombre"][] 
  children: React.ReactNode
}

export default function ProtectedRoute({ allowedRoles, children }: Props) {
  const router = useRouter()
  const role = useAuthStore((state) => state.role)

  const [isClient, setIsClient] = useState(false)
  useEffect(() => {
    setIsClient(true)
  }, [])

  useEffect(() => {
    
    if (!isClient) return

    if (!role || !allowedRoles.includes(role.nombre)) {
      router.push("/")
    }
  }, [isClient, role, allowedRoles, router])

  if (!isClient || !role || !allowedRoles.includes(role.nombre)) {
    return (
      <div className="text-center py-4 text-muted-foreground">
        Verificando permisos...
      </div>
    )
  }

  return <>{children}</>
}