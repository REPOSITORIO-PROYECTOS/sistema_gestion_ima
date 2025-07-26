'use client';

import { useState, useEffect } from "react";
import { Label } from "@/components/ui/label";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { Role, Usuario } from "@/lib/authStore";
import { useAuthStore } from "@/lib/authStore";
import { Input } from "@/components/ui/input"; 
import { toast } from "sonner"; 

export default function EditUserForm({
  user,
  onUpdated
}: {
  user: Usuario;
  onUpdated?: () => void;
}) {
  const token = useAuthStore((state) => state.token);
  const [roles, setRoles] = useState<Role[]>([]);
  const [selectedRoleId, setSelectedRoleId] = useState<number>(user.rol.id);
  const [loading, setLoading] = useState(false);
  const [nuevoNombreUsuario, setNuevoNombreUsuario] = useState(user.nombre_usuario || "");
  const [passwordActual, setPasswordActual] = useState("");
  const [passwordNueva, setPasswordNueva] = useState("");

  /* GET Roles para Editar el del user actual */
  useEffect(() => {
    async function fetchRoles() {
      if (!token) return;
      try {
        const res = await fetch(
          "https://sistema-ima.sistemataup.online/api/admin/roles",
          {
            headers: {
              Authorization: `Bearer ${token}`,
            },
          }
        );
        const data = await res.json();
        setRoles(Array.isArray(data) ? data : data.roles || []);
      } catch (e) {
        console.error("Error al obtener roles:", e);
      }
    }
    fetchRoles();
  }, [token]);

  /* DELETE Para desactivar usuario */
  const desactivarUsuario = async () => {

    if (!token || !confirm("¿Seguro que querés desactivar este usuario?")) return;
    setLoading(true);

    try {
      const res = await fetch(
        `https://sistema-ima.sistemataup.online/api/admin/usuarios/${user.id}/desactivar`,
        {
          method: "DELETE",
          headers: {
            "Authorization": `Bearer ${token}`,
          },
        }
      );

      if (!res.ok) throw new Error("Error al desactivar");
      alert("✅ Usuario desactivado.");
      onUpdated?.();

    } catch (e) {

      alert("❌ No se pudo desactivar el usuario.");
      console.log(e);

    } finally {
      
      setLoading(false);
    }
  };

  /* PATCH Para activar usuario */
  const activarUsuario = async () => {
    if (!token || !confirm("¿Seguro que querés activar este usuario?")) return;
    setLoading(true);

    try {
      const res = await fetch(
        `https://sistema-ima.sistemataup.online/api/admin/usuarios/${user.id}/activar`,
        {
          method: "PATCH",
          headers: {
            "Authorization": `Bearer ${token}`,
          },
        }
      );

      if (!res.ok) throw new Error("Error al activar");
      alert("✅ Usuario activado.");
      onUpdated?.();

    } catch (e) {
      alert("❌ No se pudo activar el usuario.");
      console.log(e);
    } finally {
      setLoading(false);
    }
  };

  /* PATCH de modificaciones de user unificado */
  const guardarCambios = async () => {
    if (!token) return;
    setLoading(true);

    try {
      // 1. Validar y cambiar rol
      if (selectedRoleId !== user.rol.id) {
        const resRol = await fetch(
          `https://sistema-ima.sistemataup.online/api/admin/usuarios/${user.id}/rol`,
          {
            method: "PATCH",
            headers: {
              "Content-Type": "application/json",
              "Authorization": `Bearer ${token}`,
            },
            body: JSON.stringify({ id_rol: selectedRoleId }),
          }
        );
        if (!resRol.ok) throw new Error("Error al cambiar el rol");
        toast.success("✅ Rol actualizado con éxito.");
      }

      // 2. Validar y cambiar nombre de usuario
      if (nuevoNombreUsuario !== user.nombre_usuario) {
        if (nuevoNombreUsuario.length < 3) {
          toast.error("❌ El nombre de usuario debe tener al menos 3 caracteres.");
        } else {
          const resNombre = await fetch("https://sistema-ima.sistemataup.online/api/me/username", {
            method: "PATCH",
            headers: {
              "Content-Type": "application/json",
              "Authorization": `Bearer ${token}`,
            },
            body: JSON.stringify({ nuevo_nombre_usuario: nuevoNombreUsuario }),
          });

          if (resNombre.status === 409) {
            toast.error("❌ Ese nombre de usuario ya está en uso.");
          } else if (!resNombre.ok) {
            throw new Error("Error al cambiar el nombre de usuario");
          } else {
            toast.success("✅ Nombre de usuario actualizado.");
          }
        }
      }

      // 3. Validar y cambiar contraseña
      if (passwordActual || passwordNueva) {
        if (!passwordActual || !passwordNueva) {
          toast.error("❌ Completá ambas contraseñas.");
        } else if (passwordNueva.length < 8) {
          toast.error("❌ La nueva contraseña debe tener al menos 8 caracteres.");
        } else {
          const resPassword = await fetch("https://sistema-ima.sistemataup.online/api/me/password", {
            method: "PATCH",
            headers: {
              "Content-Type": "application/json",
              "Authorization": `Bearer ${token}`,
            },
            body: JSON.stringify({
              password_actual: passwordActual,
              password_nueva: passwordNueva,
            }),
          });

          if (resPassword.status === 400) {
            toast.error("❌ Contraseña actual incorrecta.");
          } else if (!resPassword.ok) {
            throw new Error("Error al cambiar la contraseña");
          } else {
            toast.success("✅ Contraseña actualizada.");
            setPasswordActual("");
            setPasswordNueva("");
          }
        }
      }

      onUpdated?.();
    } catch (e) {
      toast.error("❌ Error general al guardar los cambios.");
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-4">

      {/* Rol */}
      <div>
        <Label>Seleccione un nuevo rol:</Label>
        <Select
          value={selectedRoleId.toString()}
          onValueChange={(val) => setSelectedRoleId(Number(val))}
        >
          <SelectTrigger className="mt-2 w-full">
            <SelectValue placeholder="Seleccionar nuevo rol..." />
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

      {/* Nombre de usuario */}
      <div className="space-y-2">
        <Label>Nuevo nombre de usuario</Label>
        <Input
          type="text"
          placeholder="Nombre de usuario"
          value={nuevoNombreUsuario}
          onChange={(e) => setNuevoNombreUsuario(e.target.value)}
        />
      </div>

      {/* Contraseña */}
      <div className="space-y-2">
        <Label>Contraseña actual</Label>
        <Input
          type="password"
          placeholder="********"
          value={passwordActual}
          onChange={(e) => setPasswordActual(e.target.value)}
        />

        <Label>Nueva contraseña</Label>
        <Input
          type="password"
          placeholder="********"
          value={passwordNueva}
          onChange={(e) => setPasswordNueva(e.target.value)}
        />
      </div>

      {/* Submit Modificaciones */}
      <Button
        variant="success"
        onClick={guardarCambios}
        disabled={loading}
        className="w-full"
      >
        Guardar todos los cambios
      </Button>

      <hr className="h-0.5 text-green-800"/>

      {/* Activar Usuario */}
      <Button
        variant="default"
        onClick={activarUsuario}
        disabled={loading}
        className="w-full"
      >
        Activar usuario
      </Button>

      {/* Desactivar Usuario */}
      <Button
        variant="destructive"
        onClick={desactivarUsuario}
        disabled={loading}
        className="w-full"
      >
        Desactivar usuario
      </Button>
    </div>
  );
}