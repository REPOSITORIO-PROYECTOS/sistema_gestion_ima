'use client';

import { useState, useEffect } from "react";
import { Label } from "@/components/ui/label";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { Role, Usuario } from "@/lib/authStore";
import { useAuthStore } from "@/lib/authStore";

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

  /* PATCH Para cambiar rol de usuario */
  const cambiarRol = async () => {
    if (!token) return;
    setLoading(true);
    try {
      const res = await fetch(
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
      if (!res.ok) throw new Error("Error al cambiar el rol");
      alert("✅ Rol actualizado con éxito.");
      onUpdated?.();
    } catch (e) {
      alert("❌ No se pudo actualizar el rol.");
      console.log(e);
    } finally {
      setLoading(false);
    }
  };

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

  return (
    <div className="space-y-6">
      <div>
        <Label>Rol actual</Label>
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

      {/* Modificar Rol */}
      <Button
        variant="success"
        onClick={cambiarRol}
        disabled={selectedRoleId === user.rol.id || loading}
        className="w-full"
      >
        Guardar cambios
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

      {/* Activar Usuario */}
      <Button
        variant="default"
        onClick={activarUsuario}
        disabled={loading}
        className="w-full"
      >
        Activar usuario
      </Button>
    </div>
  );
}