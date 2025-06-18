"use client";

import {
  NavigationMenu,
  NavigationMenuItem,
  NavigationMenuLink,
  NavigationMenuList,
} from "@/components/ui/navigation-menu"

import { Button } from '@/components/ui/button';
import { usePathname } from 'next/navigation'
import { useEffect, useState } from 'react';

function NavBar({ links }: { links: { href: string; name: string }[] }) {

  const pathname = usePathname();
  const [show, setShow] = useState(true);
  const [lastScrollY, setLastScrollY] = useState(0);

  /* Efecto de ocultar nav con scroll */
  useEffect(() => {

    const handleScroll = () => {
      
      const currentScrollY = window.scrollY;

      if (currentScrollY > lastScrollY) { 
        
        setShow(false); 
        
      } else { setShow(true); }

      setLastScrollY(currentScrollY);
    };

    window.addEventListener("scroll", handleScroll);

    return () => window.removeEventListener("scroll", handleScroll);

  }, [lastScrollY]);

  return (

    <header style={{ top: '72px' }} className={`fixed z-10 w-full transition-transform duration-300 ${show ? 'translate-y-0' : '-translate-y-full'}`}  >   {/* Barra verde superior */} 

      <div className="bg-white shadow px-4 py-4 flex justify-between items-center">

        {/* Pestañas NAV */}
        <NavigationMenu>
          <NavigationMenuList className="flex space-x-4">
            {links.map(({ href, name }) => {

              const isActive = pathname.startsWith(href);
              
              return (
                <NavigationMenuItem key={href}>
                  <NavigationMenuLink
                    href={href}
                    className={`text-md font-medium px-4 py-2 rounded-lg transition-colors
                    ${isActive ? 'bg-green-800 text-white' : 'text-gray-900 hover:bg-slate-200'}`}
                  >
                    {name}
                  </NavigationMenuLink>
                </NavigationMenuItem>
                )

              })}

          </NavigationMenuList>
        </NavigationMenu>

        {/* Cerrar Sesión */}
        <Button variant="destructive">Cerrar Sesión</Button>
      </div>

    </header>
  );
}

export default NavBar;