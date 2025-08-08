"use client";

import Image from "next/image";
import "../styles/globals.css";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import { Eye, EyeOff } from "lucide-react";
import { toast } from "sonner";
import { useAuthStore } from "@/lib/authStore";
import { useEmpresaStore } from "@/lib/empresaStore";
import { useProductoStore } from "@/lib/productoStore";

const API_URL = "https://sistema-ima.sistemataup.online/api";

// Tipado del producto que devuelve la API
type ProductoAPI = {
  id: number | string;
  nombre?: string;
  descripcion?: string;
  precio_venta: number;
  venta_negocio: number;
  stock_actual: number;
};

function Login() {
  const router = useRouter();

  // User Store
  const setToken = useAuthStore((state) => state.setToken);
  const setUsuario = useAuthStore((state) => state.setUsuario);
  const setRole = useAuthStore((state) => state.setRole);

  // Empresa Store
  const setEmpresa = useEmpresaStore((state) => state.setEmpresa);
  const empresa = useEmpresaStore((state) => state.empresa);

  // Catálogo de Productos
  const setProductos = useProductoStore((state) => state.setProductos);

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);

  // Fetch Periódico de Productos para la Store de Productos
  const iniciarPollingProductos = (token: string) => {
    const fetchProductos = async () => {
      try {
        const res = await fetch(`${API_URL}/articulos/obtener_todos`, {
          headers: { Authorization: `Bearer ${token}` },
        });

        if (!res.ok) throw new Error("Error al refrescar productos");

        const data: ProductoAPI[] = await res.json();
        const adaptados = data.map((p) => ({
          id: String(p.id),
          nombre: p.nombre ?? p.descripcion ?? "",
          precio_venta: p.precio_venta,
          venta_negocio: p.venta_negocio,
          stock_actual: p.stock_actual,
        }));

        setProductos(adaptados);
        localStorage.setItem("productos", JSON.stringify(adaptados));
      } catch (err) {
        console.error("Error actualizando productos:", err);
      }
    };

    // Primer fetch inmediato
    fetchProductos();

    // Refetch cada 60 segundos (puedes ajustar)
    const interval = setInterval(fetchProductos, 300000);   // cada 5 min fetch

    // Guardamos referencia por si necesitamos limpiar
    return interval;
  };

  // Login App
  const handleLogin = async (e: FormEvent) => {
    e.preventDefault();
    if (!username || !password) {
      toast.error("Por favor complete usuario y contraseña");
      return;
    }

    try {
      setLoading(true);

      // --- LOGIN ---
      const response = await fetch(`${API_URL}/auth/token`, {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: new URLSearchParams({ username, password }),
      });

      if (!response.ok) throw new Error("Credenciales inválidas");

      const { access_token } = await response.json();
      setToken(access_token);

      // --- USUARIO ---
      const meResponse = await fetch(`${API_URL}/users/me`, {
        headers: { Authorization: `Bearer ${access_token}` },
      });
      if (!meResponse.ok) throw new Error("Error al obtener datos del usuario");
      const usuario = await meResponse.json();
      setUsuario(usuario);
      setRole(usuario.rol);

      // --- EMPRESA ---
      if (!empresa) {
        const empresaResponse = await fetch(`${API_URL}/configuracion/mi-empresa`, {
          headers: { Authorization: `Bearer ${access_token}` },
        });
        if (!empresaResponse.ok) throw new Error("Error al obtener datos de la empresa");
        const dataEmpresa = await empresaResponse.json();
        setEmpresa(dataEmpresa);
      }

      // --- PRODUCTOS inicial ---
      const productosResponse = await fetch(`${API_URL}/articulos/obtener_todos`, {
        headers: { Authorization: `Bearer ${access_token}` },
      });
      if (!productosResponse.ok) throw new Error("Error al obtener catálogo de productos");
      const productosData: ProductoAPI[] = await productosResponse.json();
      const productosAdaptados = productosData.map((p) => ({
        id: String(p.id),
        nombre: p.nombre ?? p.descripcion ?? "",
        precio_venta: p.precio_venta,
        venta_negocio: p.venta_negocio,
        stock_actual: p.stock_actual,
      }));
      setProductos(productosAdaptados);
      localStorage.setItem("productos", JSON.stringify(productosAdaptados));

      // --- INICIAR POLLING ---
      const intervalId = iniciarPollingProductos(access_token);

      // Guardar intervalId si querés limpiar luego en logout
      localStorage.setItem("productosPollingId", String(intervalId));

      // --- REDIRIGIR ---
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
          disabled={loading}
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