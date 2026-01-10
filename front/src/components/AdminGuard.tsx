"use client"

import { useEffect, useMemo, useState } from "react"
import { useRouter } from "next/navigation"
import { toast } from "sonner"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"

export default function AdminGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter()
  const [ready, setReady] = useState(false)
  const [username, setUsername] = useState("")
  const [password, setPassword] = useState("")
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    setReady(true)
  }, [])

  useEffect(() => {
    if (!ready) return
    const exp = localStorage.getItem("adminGuardValidUntil")
    const valid = exp ? Number(exp) > Date.now() : false
    if (!valid) return
  }, [ready, router])

  const valid = useMemo(() => {
    const exp = typeof window !== "undefined" ? localStorage.getItem("adminGuardValidUntil") : null
    return exp ? Number(exp) > Date.now() : false
  }, [ready])

  const onSubmit = async () => {
    if (!username || !password) {
      toast.error("Ingrese usuario y contraseña")
      return
    }
    try {
      setLoading(true)
      const res = await fetch("/admin-auth", {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: new URLSearchParams({ username, password }),
        cache: "no-store",
      })
      if (!res.ok) {
        toast.error("Credenciales inválidas")
        return
      }
      const until = Date.now() + 15 * 60 * 1000
      localStorage.setItem("adminGuardValidUntil", String(until))
      toast.success("Acceso administrador habilitado")
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      {!valid && ready && (
        <Dialog open>
          <DialogContent className="sm:max-w-md">
            <DialogHeader>
              <DialogTitle>Autenticación de Administrador</DialogTitle>
            </DialogHeader>
            <div className="space-y-3">
              <div className="space-y-1">
                <label className="text-sm">Usuario</label>
                <input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="border px-3 py-2 rounded w-full"
                />
              </div>
              <div className="space-y-1">
                <label className="text-sm">Contraseña</label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="border px-3 py-2 rounded w-full"
                />
              </div>
            </div>
            <DialogFooter>
              <Button onClick={onSubmit} disabled={loading}>
                {loading ? "Ingresando..." : "Ingresar"}
              </Button>
              <Button variant="ghost" onClick={() => router.push("/dashboard")}>
                Cancelar
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}
      {valid && ready && <>{children}</>}
    </>
  )
}
