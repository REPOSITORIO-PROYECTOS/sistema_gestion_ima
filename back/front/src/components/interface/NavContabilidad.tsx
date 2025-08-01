"use client"

import { usePathname } from 'next/navigation'
import { NavigationMenu, NavigationMenuList, NavigationMenuItem, NavigationMenuLink } from "@/components/ui/navigation-menu"
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select"

function NavContabilidad({ links }: { links: { href: string; name: string }[] }) {

  const pathname = usePathname() 

  return (

    <nav className='p-4'>

      {/* Nav en escritorio */}
      <NavigationMenu className="hidden md:flex">
        <NavigationMenuList className="w-full flex flex-row justify-around md:justify-start gap-4">
          {links.map(({ href, name }) => {
            const isActive = pathname === href
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

      {/* Nav en menú dropdown para mobile */}
      <div className="md:hidden my-4">
        <Select onValueChange={(value) => (window.location.href = value)}>
          <SelectTrigger>
            <SelectValue placeholder="Elija que seccion desea ver..." />
          </SelectTrigger>
          <SelectContent >
            {links.map(({ href, name }) => (
              <SelectItem key={href} value={href}>
                {name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

    </nav>
  );
}

export default NavContabilidad;