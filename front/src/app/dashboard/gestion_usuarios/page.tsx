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
import { useEffect, /* useState  */} from "react";

// Reemplazar esto por los usuarios reales - BDD o Zustand
  const usuarios = [ 
    { id: 1, nombre: 'Juan Pérez', email: 'juan@example.com', rol: 'Admin' },
    { id: 2, nombre: 'María López', email: 'maria@example.com', rol: 'Empleado' },
  ]

  export default function GestionUsuarios() {

    /* const [llaveMaestra, setLlaveMaestra] = useState("");
 */
    useEffect(() => {
      const fetchLlave = async () => {
        try {
          const res = await fetch("https://sistema-ima.sistemataup.online/api/caja/llave-maestra"); 
          if (!res.ok) throw new Error("Error al obtener la llave");
          const data = await res.json();
          /* setLlaveMaestra(data.llave || "");  */
          console.log(data);
        } catch (error) {
          console.error("Error al traer la llave:", error);
          /* setLlaveMaestra("Error"); */
        }
      };

      fetchLlave();
    }, []);

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
            <Button variant="success" className="w-full !py-6 sm:!max-w-1/3">+ Crear nuevo usuario</Button>
          </DialogTrigger>
          <DialogContent >
            <DialogHeader>
              <DialogTitle>Crear Usuario</DialogTitle>
              <DialogDescription>Completá los datos para agregar un nuevo usuario al sistema.</DialogDescription>
            </DialogHeader>
            <UserForm />
          </DialogContent>
        </Dialog>

        {/* Llave Maestra */}
        <div className="flex flex-col sm:flex-row items-center bg-green-100 rounded-lg p-4 gap-4 w-full sm:max-w-2/3 md:max-w-1/3">
          <h2 className="text-xl font-bold text-green-950 w-2/3">Llave Caja:</h2>
          <Input type="text" value={"llavemaestra"} name="" id="" disabled className="border-2 border-green-800" />
        </div>
      </div>

      {/* Tabla de usuarios */}
      <div className="border rounded-lg overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Nombre</TableHead>
              <TableHead>Email</TableHead>
              <TableHead>Rol</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {usuarios.map((user) => (
              <TableRow key={user.id}>
                <TableCell>{user.nombre}</TableCell>
                <TableCell>{user.email}</TableCell>
                <TableCell>{user.rol}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

    </div>
  );
}