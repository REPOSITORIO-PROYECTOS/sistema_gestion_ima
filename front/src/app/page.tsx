"use client"

/* -------------------------------------------- LOGIN -------------------------------------------- */

import Image from 'next/image'
import "../styles/globals.css"

import { useRouter } from 'next/navigation'
import { Role, useAuthStore } from '@/lib/authStore'
import { FormEvent, useState } from 'react'

function Login() {

  const router = useRouter()
  const setRole = useAuthStore(state => state.setRole)
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')

  const handleLogin = (e: FormEvent) => {
    
    e.preventDefault()

    // Acá simulamos los usuarios y roles
    const users = {
      admin: { password: '123', role: 'admin' },
      cajero: { password: 'caja123', role: 'cajero' },
      contador: { password: '123', role: 'contable' }
    }

    const user = users[username as keyof typeof users]

    if (user && user.password === password) {
      setRole(user.role as Role)  // Guarda el rol en Zustand
      router.push('/dashboard')   // Redirige al dashboard inicial
    } else {
      alert('Credenciales incorrectas')
    }
  }

  return (

    <div className="flex flex-col h-screen justify-center items-center gap-10 bg-emerald-600 px-6 py-8 md:h-screen">
      
      <Image src="/logo.png" alt="Swing Jugos" width={80} height={80} />

      {/* Form Login */}
      <form onSubmit={handleLogin}
      className="form-login bg-amber-500 shadow-2xl flex flex-col items-center justify-center p-8 gap-10 rounded-4xl md:w-1/3"
      >
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
        <div className="flex flex-col gap-1">
          <label htmlFor="password" className="text-white">Contraseña</label>
          <input 
            id="password" 
            type="password" 
            value={password}
            onChange={(e) => setPassword(e.target.value)} 
              className="border !border-white text-white bg-transparent px-3 py-2 rounded focus:!outline-none focus:!ring-0 focus:!border-white hover:!border-white"

          />
        </div>

        {/* Submit */}
        <div className="w-full flex flex-col items-center gap-2 ">
          <button 
            type="submit" 
            className="flex justify-center items-center p-2 w-1/2 text-white border-2 border-white bg-amber-700 rounded-xl cursor-pointer transition hover:bg-amber-800"
          >
            Ingresar
          </button>
        </div>

        {/* Recuperar contraseña */}
        <a href="" className="text-white font-semibold hover:text-amber-900 transition">¿Olvidaste tu contraseña?</a>
      </form>

    </div>
  );
}

export default Login;