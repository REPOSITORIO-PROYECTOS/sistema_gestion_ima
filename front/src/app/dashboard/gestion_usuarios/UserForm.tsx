'use client'

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem
} from "@/components/ui/select";
import { Eye, EyeOff } from "lucide-react";
import { Role } from "@/lib/authStore";

export default function UserForm() {
  
  const [nombre_usuario, setNombreUsuario] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [roles, setRoles] = useState<Role[]>([]);
  const [selectedRoleId, setSelectedRoleId] = useState<number | undefined>();

  const passwordsMatch = password === confirm;

  // Funcion que trae los posibles roles reales del back
  useEffect(() => {
    async function fetchRoles() {
      try {
        const res = await fetch(
          "https://sistema-ima.sistemataup.online/api/admin/obtener-roles"
        );
        const data = await res.json();
        console.log("Los roles se ven asi:", data);
        if (Array.isArray(data)) {
          setRoles(data);
        } else if (Array.isArray(data.roles)) {
          setRoles(data.roles);
        } else {
          console.warn("Formato inesperado:", data);
        }
      } catch (e) {
        console.error("Error al obtener roles:", e);
      }
    }
    fetchRoles();
  }, []);

  // POST de usuarios
  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!passwordsMatch || !selectedRoleId) return;

    const newUser = {
      nombre_usuario,
      password,
      id_rol: selectedRoleId,
    };

    try {
      const res = await fetch("https://sistema-ima.sistemataup.online/api/admin/crear-usuario", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(newUser),
      });


      if (!res.ok) {
        const errorData = await res.json();
        console.error("❌ Error al crear usuario:", errorData);
        alert("No se pudo crear el usuario. Revisá los datos.");
        return;
      }

      const result = await res.json();
      console.log("✅ Usuario creado:", result);
      alert("Usuario creado exitosamente ✅");

      // Resetear formulario
      setNombreUsuario("");
      setPassword("");
      setConfirm("");
      setSelectedRoleId(undefined);

    } catch (error) {
      console.error("⚠️ Error inesperado:", error);
      alert("Ocurrió un error inesperado.");
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6 mt-4 max-w-md">
      <div>
        <Label htmlFor="nombre_usuario">Nombre</Label>
        <Input
          id="nombre_usuario"
          type="text"
          value={nombre_usuario}
          onChange={(e) => setNombreUsuario(e.target.value)} // ← ¡acá estaba el error!
          placeholder="Juan Pérez"
          className="mt-2"
        />
      </div>

      <div className="relative">
        <Label htmlFor="password">Contraseña</Label>
        <Input
          id="password"
          type={showPassword ? "text" : "password"}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="mt-2 pr-10"
        />
        <button
          type="button"
          className="absolute inset-y-0 right-3 flex items-center mt-6 cursor-pointer"
          onClick={() => setShowPassword(!showPassword)}
          tabIndex={-1}
        >
          {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
        </button>
      </div>

      <div className="relative">
        <Label htmlFor="confirm">Confirmar Contraseña</Label>
        <Input
          id="confirm"
          type={showPassword ? "text" : "password"}
          value={confirm}
          onChange={(e) => setConfirm(e.target.value)}
          className="mt-2 pr-10"
        />
        {!passwordsMatch && confirm.length > 0 && (
          <p className="text-sm text-red-500 mt-1">
            Las contraseñas no coinciden.
          </p>
        )}
      </div>

      <div>
        <Label>Rol</Label>
        <Select
          value={selectedRoleId?.toString()}
          onValueChange={(value) => setSelectedRoleId(Number(value))}
        >
          <SelectTrigger className="mt-2 w-full cursor-pointer">
            <SelectValue placeholder="Seleccionar rol..." />
          </SelectTrigger>
          <SelectContent>
            {roles.map((r) => (
              <SelectItem key={r.id} value={r.id.toString()}>
                {r.nombre}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <Button
        variant="success"
        className="w-full"
        disabled={!passwordsMatch || !selectedRoleId}
      >
        Crear Usuario
      </Button>
    </form>
  );
}