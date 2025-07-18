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

type Role = { id: number; nombre: string };

export default function UserForm() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [roles, setRoles] = useState<Role[]>([]);
  const [selectedRoleId, setSelectedRoleId] = useState<number | undefined>();

  const passwordsMatch = password === confirm;

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

  function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!passwordsMatch || !selectedRoleId) return;

    const newUser = {
      name,
      email,
      password,
      role_id: selectedRoleId,
    };

    console.log("✅ Usuario a enviar:", newUser);

    // TODO: Hacer POST al backend aquí
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6 mt-4 max-w-md">
      <div>
        <Label htmlFor="name">Nombre</Label>
        <Input
          id="name"
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Juan Pérez"
          className="mt-2"
        />
      </div>

      <div>
        <Label htmlFor="email">Email</Label>
        <Input
          id="email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="juan@mail.com"
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