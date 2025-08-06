"use client"

import {
  NavigationMenu,
  NavigationMenuItem,
  NavigationMenuLink,
  NavigationMenuList,
} from "@/components/ui/navigation-menu"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu";
import { Button } from '@/components/ui/button';
import { usePathname } from 'next/navigation'
import { useEffect, useState } from 'react';
import { useAuthStore } from '@/lib/authStore'
import { useRouter } from 'next/navigation'
import Image from 'next/image';
import { useEmpresaStore } from '@/lib/empresaStore'

type NavLink = {
  href: string
  name: string
  roles: string[]
}

// Le pasamos como prop los links (pestañas de subsecciones) y los roles para habilitar o deshabilitar accesos
function NavBar({ links, role }: { links: NavLink[], role: string }) {

  const pathname = usePathname();
  const router = useRouter();
  const usuario = useAuthStore((state) => state.usuario);
  const [show, setShow] = useState(true);
  const [lastScrollY, setLastScrollY] = useState(0);

  // Los cambios de edicion de UI en gestion_negocio se renderizan aca:
  const empresa = useEmpresaStore((state) => state.empresa);

  const navbarColor = empresa?.color_principal || 'bg-green-800';
  const logoUrl = empresa?.ruta_logo || '/default-logo.png';

  // console.log(empresa?.ruta_logo) // https://sistema-ima.sistemataup.online/api/static/logos_empresas/logo_empresa_1.png

  // Oculta NavBar en scroll
  useEffect(() => {
    const handleScroll = () => {
      const currentScrollY = window.scrollY;
      setShow(currentScrollY <= lastScrollY);
      setLastScrollY(currentScrollY);
    };

    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, [lastScrollY]);

  // Detecta las iniciales del nombre_usuario para display en avatar
  const avatarText = usuario?.nombre_usuario
  ? usuario.nombre_usuario.slice(0, 2).toUpperCase()
  : 'US';

  return (
    <nav className={`fixed top-0 z-10 w-full transition-transform duration-300 ${show ? 'translate-y-0' : '-translate-y-full'}`}>
      
      <div className={`${navbarColor} shadow px-4 py-4 flex justify-between items-center`}> 

        {/* Logo */}
        <a href="/dashboard" className="text-xl font-bold flex items-center gap-2">
          <Image
            src={`https://sistema-ima.sistemataup.online/api${logoUrl}`}
            alt="Logo Empresa"
            width={60}
            height={60}
            unoptimized
          />
        </a>

        {/* Menú de secciones - responsivo */}
        <NavigationMenu className="hidden md:block">
          <NavigationMenuList className="flex space-x-4">
            {links.map(({ href, name, roles }) => {
              const isActive = pathname.startsWith(href);
              const isAllowed = roles.includes(role);

              return (
                <NavigationMenuItem key={href}>
                  <NavigationMenuLink
                    href={isAllowed ? href : "#"}
                    onClick={(e) => {
                      if (!isAllowed) e.preventDefault();
                    }}
                    className={`text-md font-medium px-4 py-2 rounded-lg transition-colors
                      ${isAllowed
                        ? isActive
                          ? 'bg-green-600 text-white'
                          : 'text-white hover:bg-green-600 hover:text-white'
                        : 'text-gray-400 cursor-not-allowed'}
                    `}
                    aria-disabled={!isAllowed}
                  >
                    {name}
                  </NavigationMenuLink>
                </NavigationMenuItem>
              );
            })}
          </NavigationMenuList>
        </NavigationMenu>

        {/* Desplegables */}
        <div className="flex items-center">

          {/* DESKTOP - Avatar con desplegable */}
          <div className="hidden md:flex">
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <button className="cursor-pointer bg-green-300 text-gray-800 font-semibold p-2 rounded-full w-14 h-14 flex items-center justify-center">
                  {avatarText}
                </button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="bg-white">

                <DropdownMenuItem className="text-gray-600 cursor-pointer">
                  {usuario?.nombre_usuario}
                </DropdownMenuItem>

                <DropdownMenuItem 
                  className="text-black cursor-pointer"
                  onClick={() => router.push('/dashboard/panel_usuario')}
                >
                  Editar Usuario
                </DropdownMenuItem>

                <DropdownMenuSeparator />

                <DropdownMenuItem 
                  className="cursor-pointer text-red-600"
                  onClick={() => {
                    useAuthStore.getState().logout();
                    router.push('/');
                  }}
                >
                  Cerrar Sesión
                </DropdownMenuItem>

                <DropdownMenuItem 
                  className="cursor-pointer"
                  onClick={() => router.push('/dashboard/gestion_usuarios')}
                >
                  Gestión de Usuarios
                </DropdownMenuItem>

                <DropdownMenuItem 
                  className="cursor-pointer"
                  onClick={() => { router.push('/dashboard/gestion_de_negocio'); }}
                >
                  Gestión de Negocio
                </DropdownMenuItem>

              </DropdownMenuContent>
            </DropdownMenu>
          </div>

          {/* MOBILE - Menu hamburguesa */}
          <div className="md:hidden ml-2">
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" className="text-orange-500 border-white font-bold">
                  ☰
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="bg-white">
                
                <DropdownMenuItem className="text-gray-600 cursor-pointer">
                  {usuario?.nombre_usuario}
                </DropdownMenuItem>

                <DropdownMenuItem 
                  className="text-black cursor-pointer"
                  onClick={() => router.push('/dashboard/panel_usuario')}
                >
                  Editar Usuario
                </DropdownMenuItem>

                <DropdownMenuSeparator />

                {links.map(({ href, name, roles }) => {
                  const isAllowed = roles.includes(role);
                  return (
                    <DropdownMenuItem key={href} asChild>
                      <a
                        href={isAllowed ? href : "#"}
                        onClick={(e) => {
                          if (!isAllowed) e.preventDefault();
                        }}
                        className={`block py-2 text-sm ${
                          isAllowed
                            ? 'text-green-900 hover:bg-green-100'
                            : 'text-gray-400 cursor-not-allowed'
                        }`}
                      >
                        {name}
                      </a>
                    </DropdownMenuItem>
                  );
                })}

                <DropdownMenuSeparator />

                <DropdownMenuItem 
                  className="text-red-600"
                  onClick={() => {
                    useAuthStore.getState().logout();
                    router.push('/');
                  }}
                >
                  Cerrar Sesión
                </DropdownMenuItem>

                <DropdownMenuItem 
                  onClick={() => { router.push('/dashboard/gestion_usuarios'); }}
                >
                  Gestión de Usuarios
                </DropdownMenuItem>

                <DropdownMenuItem 
                  onClick={() => { router.push('/dashboard/gestion_de_negocio'); }}
                >
                  Gestión de Negocio
                </DropdownMenuItem>

              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>

      </div>
    </nav>
  );
}

export default NavBar;