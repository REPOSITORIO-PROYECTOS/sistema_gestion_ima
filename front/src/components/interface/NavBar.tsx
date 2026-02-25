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
import eventBus from "@/utils/eventBus";
import { useEmpresaStore } from "@/lib/empresaStore";
import { useCustomLinksStore } from "@/lib/customLinksStore";
import { API_CONFIG } from "@/lib/api-config";
import { useFeaturesStore } from "@/lib/featuresStore";

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
  const token = useAuthStore((state) => state.token);
  const customLinks = useCustomLinksStore((s) => s.links);
  const mesasEnabled = useFeaturesStore((s) => s.mesasEnabled);
  const setMesasEnabled = useFeaturesStore((s) => s.setMesasEnabled);

  // Scroll y ocultación del Nav
  const [show, setShow] = useState(true);
  const [lastScrollY, setLastScrollY] = useState(0);

  // Los cambios de edicion de UI en gestion_negocio se renderizan aca:
  const [logoUrl, setLogoUrl] = useState('/default-logo.png');
  const [navbarColor, setNavbarColor] = useState('bg-green-800');
  const [empresaCargada, setEmpresaCargada] = useState(false);
  const loadFromBackend = useCustomLinksStore((s) => s.loadFromBackend);


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

  // Cargar configuración de usuario al iniciar
  useEffect(() => {
    const fetchUserConfig = async () => {
      if (!token) return;

      try {
        // Obtener la configuración directamente del endpoint de config
        const res = await fetch(`${API_CONFIG.BASE_URL}/users/me/config`, {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });

        if (res.ok) {
          const configuracion = await res.json();

          if (configuracion && typeof configuracion === 'object') {
            loadFromBackend(configuracion);
          } else {
            console.warn("⚠️ Configuración vacía o inválida");
          }
        } else {
          console.error("❌ Error al obtener configuración:", res.status);
        }
      } catch (error) {
        console.error("Error fetching user config:", error);
      }
    };

    fetchUserConfig();
  }, [token, loadFromBackend]);

  useEffect(() => {
    if (!token) return;

    const hydrateFromEmpresaLinks = async () => {
      // 🔹 Solo hacer fetch si hay token disponible
      if (!token) {
        console.warn("⚠️ No hay token para hidratar links de empresa");
        return;
      }

      try {
        // 🔹 Hacer 3 requests con timeout individual y manejo de error por cada uno
        const fetchWithTimeout = (url: string, timeout = 5000) => {
          return Promise.race([
            fetch(url, {
              headers: { Authorization: `Bearer ${token}` },
              cache: "no-store",
            }),
            new Promise((_, reject) =>
              setTimeout(() => reject(new Error("Fetch timeout")), timeout)
            ),
          ]);
        };

        const results = await Promise.allSettled([
          fetchWithTimeout(`${API_CONFIG.BASE_URL}/configuracion/mi-empresa/link/1`),
          fetchWithTimeout(`${API_CONFIG.BASE_URL}/configuracion/mi-empresa/link/2`),
          fetchWithTimeout(`${API_CONFIG.BASE_URL}/configuracion/mi-empresa/link/3`),
        ]);

        const data1 = results[0].status === "fulfilled" && (results[0].value as Response).ok
          ? await (results[0].value as Response).json()
          : { link: "" };
        const data2 = results[1].status === "fulfilled" && (results[1].value as Response).ok
          ? await (results[1].value as Response).json()
          : { link: "" };
        const data3 = results[2].status === "fulfilled" && (results[2].value as Response).ok
          ? await (results[2].value as Response).json()
          : { link: "" };

        const byId = new Map(customLinks.map((link) => [link.id, link]));
        const nextLinks = ([1, 2, 3] as const).map((id) => {
          const existing = byId.get(id);
          const url =
            id === 1
              ? data1.link || existing?.url || ""
              : id === 2
                ? data2.link || existing?.url || ""
                : data3.link || existing?.url || "";

          return {
            id,
            name: existing?.name || `Enlace ${id}`,
            url,
            visible: existing?.visible ?? Boolean(url),
          };
        });

        loadFromBackend({ custom_links: nextLinks });
      } catch (error) {
        console.error("❌ Error hidratando links de empresa:", error);
        // No lanzar error, solo log. Usar valores por defecto.
      }
    };

    // 🔹 Solo ejecutar cuando el token esté disponible
    if (token) {
      hydrateFromEmpresaLinks();
    }

    // ✅ Se carga una sola vez al iniciar, sin recarga automática
  }, [token, loadFromBackend]);

  useEffect(() => {
    const obtenerEmpresa = async () => {
      try {
        const res = await fetch(`${API_CONFIG.BASE_URL}/configuracion/mi-empresa`, {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });

        if (!res.ok) throw new Error('Error al obtener datos de empresa');

        const data = await res.json();

        // Actualizar visualmente logo y color
        setNavbarColor(data.color_principal || 'bg-green-800');
        const apiBase = API_CONFIG.BASE_URL;
        const staticBase = apiBase.endsWith('/api') ? apiBase.slice(0, -4) : apiBase;
        setLogoUrl(`${staticBase}${data.ruta_logo}`);

        // Cargar estado de mesas habilitadas (desde aclaraciones_legales)
        if (data.aclaraciones_legales) {
          const mesasValue = data.aclaraciones_legales.mesas_enabled;
          const mesasHabilitadas = String(mesasValue) === "true";
          setMesasEnabled(mesasHabilitadas);
        } else {
          console.warn("⚠️ No hay aclaraciones_legales en los datos de empresa");
        }

        // Actualizar la store global
        useEmpresaStore.getState().setEmpresa(data);

      } catch (error) {
        console.error('Error al cargar datos de empresa:', error);
        setNavbarColor('bg-green-800');
        setLogoUrl('/default-logo.png');

      } finally {
        setEmpresaCargada(true);
      }
    };

    if (token) {
      obtenerEmpresa();
    }

    // Escuchar evento y refrescar los datos de empresa al recibirlo
    eventBus.on("empresa_actualizada", obtenerEmpresa);

    // Limpiar al desmontar
    return () => {
      eventBus.off("empresa_actualizada", obtenerEmpresa);
    };
  }, [token]);



  // Detecta las iniciales del nombre_usuario para display en avatar
  const avatarText = usuario?.nombre_usuario
    ? usuario.nombre_usuario.slice(0, 2).toUpperCase()
    : 'US';

  // ✅ Evitar render hasta que esté todo listo
  if (!empresaCargada || !navbarColor || !logoUrl) {
    return null;
  }

  return (
    <nav className={`fixed top-0 z-10 w-full transition-transform duration-300 ${show ? 'translate-y-0' : '-translate-y-full'}`}>

      <div className={`${navbarColor} shadow px-4 py-4 flex justify-between items-center`}>

        {/* Logo */}
        <a href="/dashboard" title="Dashboard" className="text-xl font-bold flex items-center gap-2">
          <Image
            src={logoUrl}
            alt="Logo Empresa"
            width={60}
            height={60}
            unoptimized
            onError={() => setLogoUrl('/default-logo.png')}
          />
        </a>

        {/* Menú de secciones - responsivo */}
        <NavigationMenu className="hidden md:block">
          <NavigationMenuList className="flex space-x-4">
            {links.filter(l => (mesasEnabled ? true : !l.href.startsWith('/dashboard/mesas') && !l.href.startsWith('/dashboard/cocina'))).map(({ href, name, roles }) => {
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
            {customLinks.filter((cl) => cl.visible && cl.url).map((cl) => (
              <NavigationMenuItem key={`custom-${cl.id}`}>
                <NavigationMenuLink
                  href={cl.url || "#"}
                  target="_blank"
                  rel="noopener noreferrer"
                  className={`text-md font-medium px-4 py-2 rounded-lg transition-colors
                    ${cl.url ? 'text-white hover:bg-green-600 hover:text-white' : 'text-gray-400 cursor-not-allowed'}
                  `}
                  aria-disabled={!cl.url}
                >
                  {cl.name || `Enlace ${cl.id}`}
                </NavigationMenuLink>
              </NavigationMenuItem>
            ))}
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
                  className="text-red-600"
                  onClick={() => {
                    useAuthStore.getState().logout();           // Limpia auth
                    useEmpresaStore.getState().clearEmpresa();  // Limpia empresa
                    router.push('/');                           // Redirecciona
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

                {links.filter(l => (mesasEnabled ? true : !l.href.startsWith('/dashboard/mesas') && !l.href.startsWith('/dashboard/cocina'))).map(({ href, name, roles }) => {
                  const isAllowed = roles.includes(role);
                  return (
                    <DropdownMenuItem key={href} asChild>
                      <a
                        href={isAllowed ? href : "#"}
                        onClick={(e) => {
                          if (!isAllowed) e.preventDefault();
                        }}
                        className={`block py-2 text-sm ${isAllowed
                          ? 'text-green-900 hover:bg-green-100'
                          : 'text-gray-400 cursor-not-allowed'
                          }`}
                      >
                        {name}
                      </a>
                    </DropdownMenuItem>
                  );
                })}
                {customLinks.filter((cl) => cl.visible && cl.url).map((cl) => (
                  <DropdownMenuItem key={`m-custom-${cl.id}`} asChild>
                    <a
                      href={cl.url || "#"}
                      target="_blank"
                      rel="noopener noreferrer"
                      className={`block py-2 text-sm ${cl.url ? 'text-green-900 hover:bg-green-100' : 'text-gray-400 cursor-not-allowed'
                        }`}
                    >
                      {cl.name || `Enlace ${cl.id}`}
                    </a>
                  </DropdownMenuItem>
                ))}

                <DropdownMenuSeparator />

                <DropdownMenuItem
                  className="text-red-600"
                  onClick={() => {
                    useAuthStore.getState().logout();           // Limpia auth
                    useEmpresaStore.getState().clearEmpresa();  // Limpia empresa
                    router.push('/');                           // Redirecciona
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
