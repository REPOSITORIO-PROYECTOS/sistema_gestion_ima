"use client"

import Image from 'next/image'
import "../styles/globals.css"
import { useRouter } from 'next/navigation'
import { FormEvent, useState } from 'react'
import { Eye, EyeOff } from "lucide-react"
import { useAuthStore } from '@/lib/authStore'

const API_URL = "https://sistema-ima.sistemataup.online/api"

function Login() {
  
  const router = useRouter()
  
  const setToken = useAuthStore(state => state.setToken)
  const setUsuario = useAuthStore(state => state.setUsuario)
  const setRole = useAuthStore(state => state.setRole)

  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)

  // Login App
  const handleLogin = async (e: FormEvent) => {

    e.preventDefault()

    if (!username || !password) {
      alert("Por favor complete usuario y contraseña")
      return
    }

    try {
      setLoading(true)

      // Autenticamos las credenciales en el back end
      const response = await fetch(`${API_URL}/auth/token`, {
        method: "POST",
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
        },
        body: new URLSearchParams({ username, password }),
      })

      if (!response.ok) throw new Error("Credenciales inválidas")

      const data = await response.json()
      const { access_token } = data
      /* console.log("🔑 Token recibido:", data) */ // solo para debug
      setToken(access_token)

      // Despues de autenticar, traemos los datos del usuario con:
      const meResponse = await fetch(`${API_URL}/users/me`, {
        headers: {
          Authorization: `Bearer ${access_token}`,
        },
      })

      if (!meResponse.ok) throw new Error("Error al obtener datos del usuario")

      const usuario = await meResponse.json()
      /* console.log("🙋‍♂️ Usuario recibido:", usuario) */     // solo para debug
      /* console.log("🙋‍♂️ Rol de Usuario:", usuario.rol) */ 

      // Guardar usuario y rol en el store
      setUsuario(usuario)
      setRole(usuario.rol) 

      router.push("/dashboard")

    } catch (error) {
      console.error("Error:", error)
      if (error instanceof Error) {
        alert(error.message)
      } else {
        alert("Error inesperado")
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex flex-col h-screen justify-center items-center gap-10 bg-emerald-600 px-6 py-8 md:h-screen">
      <Image src="/logo.png" alt="Swing Jugos" width={80} height={80} />

      <form onSubmit={handleLogin} className="form-login bg-amber-500 shadow-2xl flex flex-col items-center justify-center p-8 gap-10 border-3 border-orange-700 rounded-4xl md:w-1/3">
        {/* Usuario */}
        <div className="flex flex-col gap-1">
          <label htmlFor="username" className="text-white">Usuario</label>
          <input
            id="username"
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            className="border !border-white text-white bg-transparent px-3 py-2 rounded focus:!outline-none focus:!ring-0 focus:!border-white hover:!border-white"
          />
        </div>

        {/* Contraseña */}
        <div className="flex flex-col gap-1 relative">
          <label htmlFor="password" className="text-white">Contraseña</label>
          <input
            id="password"
            type={showPassword ? "text" : "password"}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="border !border-white text-white bg-transparent px-3 py-2 rounded w-full pr-10"
          />
          <button
            type="button"
            onClick={() => setShowPassword(!showPassword)}
            className="absolute right-3 top-[41px] text-white cursor-pointer"
          >
            {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
          </button>
        </div>

        {/* Submit */}
        <div className="w-full flex flex-col items-center gap-2">
          <button
            type="submit"
            disabled={loading}
            className={`flex justify-center items-center p-2 w-1/2 text-white border-2 border-white bg-amber-700 rounded-xl cursor-pointer transition hover:bg-amber-800 ${loading ? 'opacity-50 cursor-not-allowed' : ''}`}
          >
            {loading ? 'Ingresando...' : 'Ingresar'}
          </button>
        </div>

        <a href="#" className="text-white font-semibold hover:text-amber-900 transition">¿Olvidaste tu contraseña?</a>
      </form>
    </div>
  )
}

export default Login