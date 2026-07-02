'use client';

import { useState } from "react";
import { useAuthStore } from "@/lib/authStore";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { puedeModificarCredencialesPropias } from "@/lib/permisos";

export default function PanelUsuario() {

  const usuario = useAuthStore((state) => state.usuario);
  const role = useAuthStore((state) => state.role);

  const [nuevoNombreUsuario, setNuevoNombreUsuario] = useState(usuario?.nombre_usuario ?? "");
  const [passwordActual, setPasswordActual] = useState("");
  const [passwordNueva, setPasswordNueva] = useState("");
  const [loading, setLoading] = useState(false);

  const token = useAuthStore((state) => state.token);
  const puedeEditar = puedeModificarCredencialesPropias(role?.nombre);

  if (!usuario) return null;

  const handleUsernameChange = async () => {
    const confirmLogout = window.confirm(
      "Cambiar el nombre de usuario cerrará tu sesión actual y deberás volver a logearte, ¿Deseás continuar?"
    );
    if (!confirmLogout) return;

    try {
      setLoading(true);
      const res = await fetch("https://sistema-ima.sistemataup.online/api/users/me/username", {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          nuevo_nombre_usuario: nuevoNombreUsuario,
        }),
      });

      if (!res.ok) {
        const error = await res.json();
        throw new Error(error.detail || "Error al cambiar el nombre de usuario");
      }

      toast.success("Nombre de usuario actualizado. Cerrando sesión...");
      useAuthStore.getState().logout();
      window.location.href = "/";

    } catch (error) {
      console.log(error);
      toast.error("Ocurrió un error al cambiar el nombre de usuario");
    } finally {
      setLoading(false);
    }
  };

  const handlePasswordChange = async () => {
    if (!passwordActual || !passwordNueva) {
      toast.warning("Completa ambos campos de contraseña");
      return;
    }

    if (passwordActual === passwordNueva) {
      toast.warning("La nueva contraseña no puede ser igual a la actual");
      return;
    }

    try {
      setLoading(true);
      const res = await fetch("https://sistema-ima.sistemataup.online/api/users/me/password", {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          password_actual: passwordActual,
          password_nueva: passwordNueva,
        }),
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || "Error al cambiar la contraseña");
      }

      toast.success("Contraseña actualizada");
      setPasswordActual("");
      setPasswordNueva("");

    } catch (error) {
      console.error(error);
      toast.error(error instanceof Error ? error.message : "Error al cambiar la contraseña");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col gap-6 p-4 max-w-lg">

      <div className="space-y-4">
        <h2 className="text-3xl font-bold text-green-950">Panel de Usuario</h2>
        <p className="text-muted-foreground">
          {puedeEditar
            ? "Administrá tu usuario. Acá podés modificar tu nombre y contraseña."
            : "Datos de tu usuario. Para cambiar contraseña o nombre, contactá a un administrador."}
        </p>
      </div>

      <div className="space-y-3">
        <h3 className="text-xl font-semibold">Nombre de usuario</h3>
        <Input
          value={nuevoNombreUsuario}
          onChange={(e) => setNuevoNombreUsuario(e.target.value)}
          disabled={!puedeEditar}
        />
        {puedeEditar && (
          <Button
            onClick={handleUsernameChange}
            disabled={loading || nuevoNombreUsuario === usuario.nombre_usuario}
          >
            Guardar cambios
          </Button>
        )}
      </div>

      {puedeEditar ? (
        <div className="space-y-3">
          <h3 className="text-xl font-semibold">Cambiar contraseña</h3>
          <Input
            type="password"
            placeholder="Contraseña actual"
            value={passwordActual}
            onChange={(e) => setPasswordActual(e.target.value)}
          />
          <Input
            type="password"
            placeholder="Nueva contraseña"
            value={passwordNueva}
            onChange={(e) => setPasswordNueva(e.target.value)}
          />
          <Button onClick={handlePasswordChange} disabled={loading}>
            Cambiar contraseña
          </Button>
        </div>
      ) : (
        <div className="rounded-md border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
          Rol actual: <strong>{role?.nombre ?? "—"}</strong>. No tenés permiso para modificar credenciales.
        </div>
      )}
    </div>
  );
}
