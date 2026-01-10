"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { API_CONFIG } from "@/lib/api-config";
import { useAuthStore } from "@/lib/authStore";

const API_URL = API_CONFIG.BASE_URL;

export default function AdminLogin() {
  const router = useRouter();
  const setToken = useAuthStore((s) => s.setToken);
  const setUsuario = useAuthStore((s) => s.setUsuario);
  const setRole = useAuthStore((s) => s.setRole);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!username || !password) {
      toast.error("Ingrese usuario y contraseña");
      return;
    }
    try {
      setLoading(true);
      let response: Response;
      try {
        response = await fetch(`${API_URL}/auth/token`, {
          method: "POST",
          headers: { "Content-Type": "application/x-www-form-urlencoded" },
          body: new URLSearchParams({ username, password }),
          cache: "no-store",
        });
      } catch {
        await new Promise((r) => setTimeout(r, 250));
        response = await fetch(`${API_URL}/auth/token`, {
          method: "POST",
          headers: { "Content-Type": "application/x-www-form-urlencoded" },
          body: new URLSearchParams({ username, password }),
          cache: "no-store",
        });
      }
      if (!response.ok) throw new Error("Credenciales inválidas");
      const { access_token } = await response.json();
      setToken(access_token);
      const me = await fetch(`${API_URL}/users/me`, {
        headers: { Authorization: `Bearer ${access_token}` },
      });
      if (!me.ok) throw new Error("Error al obtener usuario");
      const usuario = await me.json();
      setUsuario(usuario);
      setRole(usuario.rol);
      const nombreRol = usuario?.rol?.nombre;
      if (!["Admin", "Soporte"].includes(nombreRol)) {
        throw new Error("Acceso restringido a administradores");
      }
      const until = Date.now() + 15 * 60 * 1000;
      localStorage.setItem("adminGuardValidUntil", String(until));
      toast.success("Acceso de administrador concedido");
      router.push("/dashboard/configuracion/empresas");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Error inesperado");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-neutral-900 px-6">
      <form onSubmit={handleSubmit} className="w-full max-w-md bg-white rounded-lg shadow p-6 space-y-4">
        <h1 className="text-xl font-semibold">Acceso Administrador</h1>
        <div className="space-y-2">
          <label className="text-sm">Usuario</label>
          <input
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            className="border px-3 py-2 rounded w-full"
          />
        </div>
        <div className="space-y-2">
          <label className="text-sm">Contraseña</label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="border px-3 py-2 rounded w-full"
          />
        </div>
        <button
          type="submit"
          disabled={loading}
          className={`w-full py-2 rounded text-white ${loading ? "bg-gray-400" : "bg-blue-600 hover:bg-blue-700"}`}
        >
          {loading ? "Ingresando..." : "Ingresar"}
        </button>
      </form>
    </div>
  );
}
