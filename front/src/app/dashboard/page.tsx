"use client"

import Image from 'next/image'

export default function Inicio() {

  return (

    /* Página Bienvenida */
    <div className="flex flex-col items-center gap-4">

      <h1 className="text-3xl font-bold text-green-950">HOLA ESTO ES PRUEBA</h1>
      
      <Image src="/intro.png" alt="Swing Jugos" width={500} height={500} className="rounded-lg" />

    </div>
  );
}