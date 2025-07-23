'use client';

import {
  Dialog,
  DialogTrigger,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import UserForm from "./UserForm";
import { Input } from "@/components/ui/input";
import { useEffect, useState } from "react";
import { useAuthStore } from "@/lib/authStore";
import { Usuario } from "@/lib/authStore";
import { useFacturacionStore } from "@/lib/facturacionStore";
import * as Switch from '@radix-ui/react-switch';

export default function GestionUsuarios() {

  const [llaveMaestra, setLlaveMaestra] = useState("");
  const [usuarios, setUsuarios] = useState<Usuario[]>([]);
  const token = useAuthStore((state) => state.token);
  const { habilitarExtras, toggleExtras } = useFacturacionStore();

  // Fetch de llave maestra
  useEffect(() => {
    if (!token) return;

    const fetchLlave = async () => {
      try {
        const res = await fetch("https://sistema-ima.sistemataup.online/api/auth/llave-actual", {
          headers: {
            'x-admin-token': token,
          },
        });

        if (!res.ok) throw new Error("Error al obtener la llave");
        const data = await res.json();
        setLlaveMaestra(data.llave_maestra || "No Disponible");
      } catch (error) {
        console.error("Error al traer la llave:", error);
        setLlaveMaestra("Error");
      }
    };

    fetchLlave();
  }, [token]);

  // GET - Usuarios de la app
  useEffect(() => {
    if (!token) return;

    const fetchUsuarios = async () => {
      try {
        const res = await fetch("https://sistema-ima.sistemataup.online/api/admin/usuarios/listar", {
          headers: {
            'x-admin-token': token,
          },
        });

        if (!res.ok) throw new Error("Error al obtener usuarios");
        const data = await res.json();
        setUsuarios(data); 
        console.log(data)

      } catch (error) {

        console.error("Error al traer usuarios:", error);
        setUsuarios([]);
      }
    };

    fetchUsuarios();
  }, [token]);

  return (
    <div className="flex flex-col gap-6 p-2">

      {/* Header */}
      <div className="space-y-2">
        <h2 className="text-3xl font-bold text-green-950">Gestión de Usuarios</h2>
        <p className="text-muted-foreground">Administrá los usuarios de tu aplicación.</p>
      </div>

      {/* Header de la Tabla */}
      <div className="flex flex-col-reverse gap-4 sm:flex-row sm:justify-between items-center">

        {/* Botón + Modal */}
        <Dialog>
          <DialogTrigger asChild>
            <Button variant="success" className="w-full !py-6 sm:!max-w-1/4 text-lg font-semibold">+ Crear nuevo usuario</Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Crear Usuario</DialogTitle>
              <DialogDescription>Completá los datos para agregar un nuevo usuario al sistema.</DialogDescription>
            </DialogHeader>
            <UserForm />
          </DialogContent>
        </Dialog>

        {/* Llave Maestra */}
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <div className="flex flex-col sm:flex-row items-center bg-green-100 rounded-lg px-4 py-3 gap-4 w-full sm:max-w-2/3 md:max-w-1/4 cursor-help">
                <h2 className="text-xl font-bold text-green-950 w-2/3">Llave Caja:</h2>
                <Input
                  type="text"
                  value={llaveMaestra}
                  disabled
                  className="border-2 border-green-800 text-center w-1/2"
                />
              </div>
            </TooltipTrigger>
            <TooltipContent side="top" className="bg-green-200 text-green-900">
              Con esta llave podés abrir la caja en la sección Ventas.
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      </div>

      {/* Tabla de usuarios */}
      <div className="border rounded-lg overflow-hidden">
        <Table>

          <TableHeader>
            <TableRow>
              <TableHead className="px-4">Nombre</TableHead>
              <TableHead className="px-4">Rol</TableHead>
            </TableRow>
          </TableHeader>

          <TableBody>
            {usuarios.length === 0 ? (
              <TableRow>
                <TableCell colSpan={2} className="text-center">No hay usuarios disponibles.</TableCell>
              </TableRow>
            ) : (
              usuarios.map((user) => (
                <TableRow key={user.id}>
                  <TableCell className="px-4">{user.nombre_usuario}</TableCell>
                  <TableCell className="px-4">{user.rol.nombre}</TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

       {/* Toggle de Facturación en Caja */}
      <div className="flex items-center gap-4">
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

    </div>
  );
}