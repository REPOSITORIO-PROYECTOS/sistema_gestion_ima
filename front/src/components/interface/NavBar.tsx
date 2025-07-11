"use client"

import {
  NavigationMenu,
  NavigationMenuItem,
  NavigationMenuLink,
  NavigationMenuList,
} from "@/components/ui/navigation-menu"

import { Button } from '@/components/ui/button';
import { usePathname } from 'next/navigation'
import { useEffect, useState } from 'react';

import { useAuthStore } from '@/lib/authStore'
import { useRouter } from 'next/navigation'

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

    <nav style={{ top: '72px' }} className={`fixed z-10 w-full transition-transform duration-300 ${show ? 'translate-y-0' : '-translate-y-full'}`}>
      
      <div className="bg-white shadow px-4 py-4 flex justify-between items-center">

        {/* Barra de Navegacion de Secciones */}
        <NavigationMenu>
          <NavigationMenuList className="flex space-x-4">

            {links.map(({ href, name, roles }) => {

              // Mapeamos por si existe subseccion y si el rol lo permite
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
                          ? 'bg-green-800 text-white'
                          : 'text-gray-900 hover:bg-slate-200'
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

        {/* Cerrar Sesión y volver al login */}
        <Button
          variant="destructive"
          onClick={() => {
            useAuthStore.getState().logout();   
            router.push('/');
          }}
        >
          Cerrar Sesión
        </Button>
      </div>
      
    </nav>
  );
}

export default NavBar;