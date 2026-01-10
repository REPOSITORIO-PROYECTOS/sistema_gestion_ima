"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { useAuthStore } from "@/lib/authStore"

export default function AdminGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter()
  const role = useAuthStore((state) => state.role)
  const [ready, setReady] = useState(false)

  useEffect(() => {
    setReady(true)
  }, [])

  useEffect(() => {
    if (!ready) return
    if (!role || !["Admin", "Soporte"].includes(role.nombre)) {
      router.push("/")
      return
    }
    const exp = localStorage.getItem("adminGuardValidUntil")
    const valid = exp ? Number(exp) > Date.now() : false
    if (!valid) {
      router.push("/admin/login")
    }
  }, [ready, role, router])

  if (!ready || !role || !["Admin", "Soporte"].includes(role.nombre)) {
    return <div className="text-center py-4 text-muted-foreground">Verificando acceso...</div>
  }
  const exp = typeof window !== "undefined" ? localStorage.getItem("adminGuardValidUntil") : null
  const valid = exp ? Number(exp) > Date.now() : false
  if (!valid) {
    return <div className="text-center py-4 text-muted-foreground">Requiere autenticación de administrador...</div>
  }
  return <>{children}</>
}
