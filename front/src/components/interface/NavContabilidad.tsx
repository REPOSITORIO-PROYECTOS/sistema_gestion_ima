"use client"

import { usePathname } from 'next/navigation'

import { 
  NavigationMenu, 
  NavigationMenuItem, 
  NavigationMenuLink, 
  NavigationMenuList 
} from "@radix-ui/react-navigation-menu";


function NavContabilidad({ links }: { links: { href: string; name: string }[] }) {

  const pathname = usePathname()

  return (
    
    <div>

      <NavigationMenu>
        <NavigationMenuList className="flex space-x-4">
              {links.map(({ href, name }) => {

              const isActive = pathname === href

                return (
                  <NavigationMenuItem key={href}>
                    <NavigationMenuLink href={href} className={`text-md font-medium px-4 py-2 rounded-lg transition-colors
                      ${isActive ? 'bg-green-800 text-white' : 'text-gray-900 hover:bg-slate-200'}`} >
                      {name}
                    </NavigationMenuLink>
                  </NavigationMenuItem>
                )
                
              })}
        </NavigationMenuList>
      </NavigationMenu>

    </div>
  );

}

export default NavContabilidad;