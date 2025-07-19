'use client';

import {
  Dialog,
  DialogTrigger,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import UserForm from "./UserForm";
import { Input } from "@/components/ui/input";
import { useEffect, useState } from "react";
import { useAuthStore } from "@/lib/authStore";
import { Usuario } from "@/lib/authStore";

export default function GestionUsuarios() {

  const [llaveMaestra, setLlaveMaestra] = useState("");
  const [usuarios, setUsuarios] = useState<Usuario[]>([]);
  const token = useAuthStore((state) => state.token);

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
        const res = await fetch("https://sistema-ima.sistemataup.online/api/admin/usuarios", {
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
        <p className="text-muted-foreground">Administrá los usuarios de la aplicación.</p>
      </div>

      {/* Header de la Tabla */}
      <div className="flex flex-col-reverse gap-4 sm:flex-row sm:justify-between items-center">

        {/* Botón + Modal */}
        <Dialog>
          <DialogTrigger asChild>
            <Button variant="success" className="w-full !py-6 sm:!max-w-1/4">+ Crear nuevo usuario</Button>
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
        <div className="flex flex-col sm:flex-row items-center bg-green-100 rounded-lg px-4 py-3 gap-4 w-full sm:max-w-2/3 md:max-w-1/4">
          <h2 className="text-xl font-bold text-green-950 w-2/3">Llave Caja:</h2>
          <Input
            type="text"
            value={llaveMaestra}
            disabled
            className="border-2 border-green-800 text-center w-1/2"
          />
        </div>
      </div>

      {/* Tabla de usuarios */}
      <div className="border rounded-lg overflow-hidden">
        <Table>

          <TableHeader>
            <TableRow>
              <TableHead>Nombre</TableHead>
              <TableHead>Rol</TableHead>
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
                  <TableCell>{user.nombre_usuario}</TableCell>
                  <TableCell>{user.rol.nombre}</TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}