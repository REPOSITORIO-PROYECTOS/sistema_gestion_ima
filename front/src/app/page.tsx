"use client"

import Link from 'next/link'
import Image from 'next/image'
import "../styles/globals.css"

function Login() {
  
  return (

    <div className="flex flex-col h-screen justify-center items-center gap-10 bg-emerald-600">
     
      <Image src="/logo.png" alt="Swing Jugos" width={70} height={70} />

      <form 
      className="form-login bg-amber-500 shadow-2xl flex flex-col items-center justify-center w-1/3 p-8 gap-10 rounded-4xl"
      action="">

        <div className="flex flex-col gap-2">
          <label htmlFor="name" className="text-white">Usuario</label>
          <input id="name" type="text" />
        </div>

        <div className="flex flex-col gap-2">
          <label htmlFor="name" className="text-white">Contraseña</label>
          <input id="name" type="password" />
        </div>

        <div className="w-full flex flex-col items-center gap-2 ">
          <Link href="/dashboard"
          className="flex justify-center items-center p-2 w-1/2 text-white border-2 border-white rounded-xl cursor-pointer transition hover:bg-amber-700"
          type="submit">Ingresar</Link>
        </div>

        <a href="" className="text-black">¿Olvidaste tu contraseña?</a>

      </form>

    </div>

  );
}

export default Login;