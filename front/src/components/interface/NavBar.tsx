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

type NavLink = {
  href: string
  name: string
  roles: string[]
}

// Le pasamos como prop los links (pestañas de subsecciones) y los roles para habilitar o deshabilitar accesos
function NavBar({ links, role }: { links: NavLink[], role: string }) {

  const pathname = usePathname();
  const [show, setShow] = useState(true);
  const [lastScrollY, setLastScrollY] = useState(0);
  const router = useRouter();

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

  return (

    <nav className={`fixed top-0 z-10 w-full transition-transform duration-300 ${show ? 'translate-y-0' : '-translate-y-full'}`}>
      <div className="bg-green-800 shadow px-4 py-4 flex justify-between items-center">

        {/* Logo */}
        <a href="/dashboard" className="text-xl font-bold flex items-center gap-2">
          <Image src="/logo.png" alt="Swing Jugos" width={60} height={60} />
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
                          ? 'bg-green-700 text-white'
                          : 'text-white hover:bg-green-500 hover:text-green-900'
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

          {/* Avatar con desplegable cerrar sesion */}
          <div className="hidden md:flex">
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <button className="cursor-pointer bg-green-300 text-gray-800 font-semibold p-2 rounded-full w-12 h-12 flex items-center justify-center">
                  IM
                </button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="bg-white">
                <DropdownMenuItem 
                  className="cursor-pointer text-red-600"
                  onClick={() => {
                    useAuthStore.getState().logout();
                    router.push('/');
                  }}
                >
                  Cerrar Sesión
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>

          {/* Menu hamburguesa mobile */}
          <div className="md:hidden ml-2">
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" className="text-orange-500 border-white font-bold">
                  ☰
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="bg-white">
                {links.map(({ href, name, roles }) => {
                  const isAllowed = roles.includes(role);
                  return (
                    <DropdownMenuItem key={href} asChild>
                      <a
                        href={isAllowed ? href : "#"}
                        onClick={(e) => {
                          if (!isAllowed) e.preventDefault();
                        }}
                        className={`block px-4 py-2 text-sm ${
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
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>

      </div>
    </nav>
  );
}

export default NavBar;