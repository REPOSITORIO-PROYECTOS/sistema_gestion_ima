"use client"

import Image from 'next/image'
import "../styles/globals.css"
import { useRouter } from 'next/navigation'
import { FormEvent, useState } from 'react'
import { Eye, EyeOff } from "lucide-react"
import { useAuthStore } from '@/lib/authStore'
import { useEmpresaStore } from '@/lib/empresaStore'

const API_URL = "https://sistema-ima.sistemataup.online/api"

function Login() {
  
  const router = useRouter()
  
  // User Store
  const setToken = useAuthStore(state => state.setToken)
  const setUsuario = useAuthStore(state => state.setUsuario)
  const setRole = useAuthStore(state => state.setRole)

  // Empresa Store
  const setEmpresa = useEmpresaStore(state => state.setEmpresa) // ✅ HOOK NUEVO
  const empresa = useEmpresaStore(state => state.empresa)

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

      // Guardar usuario y rol en el store
      setUsuario(usuario)
      setRole(usuario.rol) 

      // Empresa (sólo si no está ya seteada)
      if (!empresa) {
        const empresaResponse = await fetch(`${API_URL}/configuracion/mi-empresa`, {
          headers: {
            Authorization: `Bearer ${access_token}`,
          },
        })

        if (!empresaResponse.ok) throw new Error("Error al obtener datos de la empresa")

        const dataEmpresa = await empresaResponse.json()
        setEmpresa(dataEmpresa) 
        console.log("🏢 Empresa cargada:", dataEmpresa)
      }

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
    <div className="flex flex-col h-screen justify-center items-center gap-10 bg-sky-700 px-8 py-8 md:h-screen">
      
      <Image src="/logo_software.png" alt="Swing Jugos" width={80} height={80} />

      <form onSubmit={handleLogin} className="w-[95%] sm:w-1/2 lg:w-1/3 form-login bg-slate-100 shadow-2xl flex flex-col items-center justify-center p-10 gap-10 rounded-4xl">
        
        {/* Usuario */}
        <div className="flex flex-col gap-1 relative">
          <label htmlFor="username" className="text-sky-800">Usuario</label>
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
          <label htmlFor="password" className="text-sky-800">Contraseña</label>
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
          className={`flex w-4/5 sm:max-w-1/2 sm:w-1/2 justify-center items-center px-4 py-3 text-white border-2 border-white bg-blue-700 rounded-xl cursor-pointer transition hover:bg-sky-800 ${loading ? 'opacity-50 cursor-not-allowed' : ''}`}
        >
          {loading ? 'Ingresando...' : 'Ingresar'}
        </button>
 
      </form>
    </div>
  )
}

export default Login