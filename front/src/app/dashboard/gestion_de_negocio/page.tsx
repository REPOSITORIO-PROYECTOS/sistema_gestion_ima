'use client';

import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem
} from "@/components/ui/select"
import { useFacturacionStore } from '@/lib/facturacionStore';
import * as Switch from '@radix-ui/react-switch';
import { useThemeStore } from '@/lib/themeStore'
import { Input } from "@/components/ui/input";
import Image from "next/image"
import { useRef } from "react";

export default function GestionNegocio() {

  const { habilitarExtras, toggleExtras } = useFacturacionStore();
  const { setNavbarColor, setLogoUrl, navbarColor, logoUrl } = useThemeStore()

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    const allowedTypes = ["image/png", "image/jpeg", "image/webp"]
    if (!allowedTypes.includes(file.type)) {
      alert("Formato no permitido. Solo .png, .jpg, .webp")
      return
    }

    const reader = new FileReader()
    reader.onload = () => {
      const dataUrl = reader.result as string
      setLogoUrl(dataUrl) // guarda el base64 como URL
    }
    reader.readAsDataURL(file)
  }

  const fileInputRef = useRef<HTMLInputElement>(null)

  return (
    <div className="flex flex-col gap-6 p-2">

      {/* Header */}
      <div className="space-y-2">
        <h2 className="text-3xl font-bold text-green-950">Gestión de Negocio</h2>
        <p className="text-muted-foreground">Administrá los usuarios de tu aplicación.</p>
      </div>

      {/* Toggle de Facturación en Caja */}
      <div className="flex flex-col sm:flex-row items-center gap-4">
        <h3 className="text-lg font-semibold text-green-950">
          Habilitar Remito / Presupuesto
        </h3>

        <Switch.Root
          checked={habilitarExtras}
          onCheckedChange={toggleExtras}
          className={`relative w-16 h-8 rounded-full ${
            habilitarExtras ? "bg-green-900" : "bg-gray-300"
          } cursor-pointer transition-colors`}
        >
          <Switch.Thumb
            className={`absolute top-1 left-1 w-6 h-6 bg-white rounded-full shadow-md transition-transform duration-300 ${
              habilitarExtras ? "translate-x-8" : "translate-x-0"
            }`}
          />
        </Switch.Root>
      </div>

      <hr className="h-0.25 my-4" />

      {/* Header para personalización */}
      <div className="space-y-2">
        <h2 className="text-2xl font-bold text-green-950">Configuración de la Apariencia</h2>
        <p className="text-muted-foreground">Administrá la apariencia de tu aplicación.</p>
      </div>

      {/* Configuración de Negocios */}
      <div className="flex flex-col items-start gap-8 p-4">

        {/* Color del Nav */}
        <div className="flex flex-col gap-2">
          <label className="block text-md font-semibold mb-1">Color de la barra de Navegación</label>
          
          <Select value={navbarColor} onValueChange={setNavbarColor}>
            <SelectTrigger className="w-2/3 cursor-pointer">
              <SelectValue placeholder="Selecciona un color" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="bg-green-800">Verde Oscuro</SelectItem>
              <SelectItem value="bg-blue-800">Azul Oscuro</SelectItem>
              <SelectItem value="bg-red-800">Rojo Oscuro</SelectItem>
              <SelectItem value="bg-gray-800">Gris Oscuro</SelectItem>
            </SelectContent>
          </Select>
          
        </div>

        {/* Switch de Imagen */}
        <div className="flex flex-col items-start gap-4 mb-6">
          <label className="text-md font-semibold mb-1">Logo actual:</label>
          <div className="flex flex-col sm:flex-row items-center gap-4">
            <Image src={logoUrl} alt="Logo actual" width={60} height={60} />
            <Input
              type="file"
              accept=".png,.jpg,.jpeg,.webp"
              onChange={handleFileChange}
              ref={fileInputRef}
              className="max-w-sm"
            />
          </div>
        </div>
    </div>

    </div>
  );
}