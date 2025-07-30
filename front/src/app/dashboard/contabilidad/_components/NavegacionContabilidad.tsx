// app/(dashboard)/contabilidad/_components/NavegacionContabilidad.tsx
'use client';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

export function NavegacionContabilidad() {
  const pathname = usePathname();
  const tabs = [ { nombre: 'Libro Mayor', href: '/contabilidad' } ];
  return (
    <nav className="border-b border-gray-200">
      <ul className="flex space-x-4">
        {tabs.map((tab) => (
          <li key={tab.href}>
            <Link href={tab.href} className={`pb-2 px-1 text-sm font-medium ${pathname === tab.href ? 'border-b-2 border-blue-500 text-blue-600' : 'text-gray-500 hover:text-gray-700'}`}>
              {tab.nombre}
            </Link>
          </li>
        ))}
      </ul>
    </nav>
  );
}