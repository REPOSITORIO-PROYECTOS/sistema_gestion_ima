"use client";

import Image from "next/image";
import "../styles/globals.css";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";
import { Eye, EyeOff } from "lucide-react";
import { toast } from "sonner";
import { useAuthStore } from "@/lib/authStore";
import { useEmpresaStore } from "@/lib/empresaStore";
import { API_CONFIG } from "@/lib/api-config";

const API_URL = API_CONFIG.BASE_URL;

function Login() {
  const router = useRouter();

  // User Store
  const setToken = useAuthStore((state) => state.setToken);
  const setUsuario = useAuthStore((state) => state.setUsuario);
  const setRole = useAuthStore((state) => state.setRole);

  // Empresa Store
  const setEmpresa = useEmpresaStore((state) => state.setEmpresa);
  const empresa = useEmpresaStore((state) => state.empresa);

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [failedAttempts, setFailedAttempts] = useState(0);
  const [cooldownUntil, setCooldownUntil] = useState<number | null>(null);

  useEffect(() => {
    if (!cooldownUntil) return;
    const timer = setInterval(() => {
      if (Date.now() >= cooldownUntil) {
        setCooldownUntil(null);
      }
    }, 1000);
    return () => clearInterval(timer);
  }, [cooldownUntil]);

  const handleLogin = async (e: FormEvent) => {
    e.preventDefault();
    if (!username || !password) {
      toast.error("Por favor complete usuario y contraseña");
      return;
    }

    if (cooldownUntil && Date.now() < cooldownUntil) {
      const secs = Math.ceil((cooldownUntil - Date.now()) / 1000);
      toast.error(`Espere ${secs}s antes de volver a intentar`);
      return;
    }

    try {
      setLoading(true);

      const response = await fetch(`${API_URL}/auth/token`, {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: new URLSearchParams({ username, password }),
        cache: "no-store",
      });

      if (response.status === 429) {
        const retryAfter = Number(response.headers.get("Retry-After") || "60");
        setCooldownUntil(Date.now() + retryAfter * 1000);
        throw new Error("Demasiados intentos. Espere un momento e intente de nuevo.");
      }

      if (!response.ok) {
        const nextFailed = failedAttempts + 1;
        setFailedAttempts(nextFailed);
        if (nextFailed >= 3) {
          setCooldownUntil(Date.now() + 30_000);
          setFailedAttempts(0);
        }
        throw new Error("Credenciales inválidas");
      }

      setFailedAttempts(0);
      setCooldownUntil(null);

      const { access_token } = await response.json();
      setToken(access_token);

      // --- USUARIO + EMPRESA en paralelo ---
      const [meResponse, empresaResponse] = await Promise.all([
        fetch(`${API_URL}/users/me`, {
          headers: { Authorization: `Bearer ${access_token}` },
        }),
        !empresa
          ? fetch(`${API_URL}/configuracion/mi-empresa`, {
              headers: { Authorization: `Bearer ${access_token}` },
            })
          : Promise.resolve(null),
      ]);

      if (!meResponse.ok) throw new Error("Error al obtener datos del usuario");
      const usuario = await meResponse.json();
      setUsuario(usuario);
      setRole(usuario.rol);

      if (empresaResponse) {
        if (!empresaResponse.ok) throw new Error("Error al obtener datos de la empresa");
        const dataEmpresa = await empresaResponse.json();
        setEmpresa(dataEmpresa);
      }

      router.push("/dashboard");
    } catch (error) {
      console.error("Error:", error);
      toast.error(error instanceof Error ? error.message : "Error inesperado");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-screen justify-center items-center gap-10 bg-sky-700 px-8 py-8 md:h-screen">
      <Image
        src="/default-logo.png"
        alt="Swing Jugos"
        width={80}
        height={80}
      />

      <form
        onSubmit={handleLogin}
        className="w-[95%] sm:w-1/2 lg:w-1/3 form-login bg-slate-100 shadow-2xl flex flex-col items-center justify-center p-10 gap-10 rounded-4xl"
      >
        {/* Usuario */}
        <div className="flex flex-col gap-1 relative">
          <label htmlFor="username" className="text-sky-800">
            Usuario
          </label>
          <input
            id="username"
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            className="border !border-sky-800 text-sky-800 bg-transparent px-3 py-2 rounded w-full focus:!outline-none focus:!ring-0 focus:!border-sky-800"
          />
        </div>

        {/* Contraseña */}
        <div className="flex flex-col gap-1 relative">
          <label htmlFor="password" className="text-sky-800">
            Contraseña
          </label>
          <input
            id="password"
            type={showPassword ? "text" : "password"}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="border !border-sky-800 text-sky-800 bg-transparent px-3 py-2 rounded w-full pr-10"
          />
          <button
            type="button"
            onClick={() => setShowPassword(!showPassword)}
            className="absolute right-3 top-[41px] text-sky-800 cursor-pointer"
          >
            {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
          </button>
        </div>

        {/* Submit */}
        <button
          type="submit"
          disabled={loading || (cooldownUntil !== null && Date.now() < cooldownUntil)}
          className={`flex w-4/5 sm:max-w-1/2 sm:w-1/2 justify-center items-center px-4 py-3 text-white border-2 border-white bg-blue-700 rounded-xl cursor-pointer transition hover:bg-sky-800 ${
            loading ? "opacity-50 cursor-not-allowed" : ""
          }`}
        >
          {loading ? "Ingresando..." : "Ingresar"}
        </button>
      </form>
    </div>
  );
}

export default Login;
