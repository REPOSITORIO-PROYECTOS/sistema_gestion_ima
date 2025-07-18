// Componente reutilizable

import { Button } from "@/components/ui/button";


export default function UserForm() {



  return (

    <form className="space-y-4 mt-4">

      <div>
        <label className="block text-sm font-medium">Nombre</label>
        <input type="text" className="mt-1 block w-full border px-3 py-2 rounded-md" />
      </div>

      <div>
        <label className="block text-sm font-medium">Email</label>
        <input type="email" className="mt-1 block w-full border px-3 py-2 rounded-md" />
      </div>

      <div>
        <label className="block text-sm font-medium">Rol</label>
        <select className="mt-1 block w-full border px-3 py-2 rounded-md">
          <option>Administrador</option>
          <option>Cajero</option>
          <option>Gerente</option>
          <option>Soporte</option>
        </select>
      </div>

      <Button type="submit" variant="success" className="w-full">Crear Usuario</Button>
    </form>

  );
}