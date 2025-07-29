// src/components/ui/FormattedDate.tsx
"use client";

// Definimos las propiedades que aceptará el componente
interface FormattedDateProps {
  isoString: string | null | undefined;
  
  // Opcional: para formatos más cortos, por ejemplo, sin la hora
  options?: Intl.DateTimeFormatOptions;
}

// El valor por defecto para las opciones de formato
const defaultOptions: Intl.DateTimeFormatOptions = {
  day: '2-digit',
  month: '2-digit',
  year: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
};

export default function FormattedDate({ isoString, options = defaultOptions }: FormattedDateProps) {
  
  // Si no hay fecha, no renderizamos nada para evitar errores
  if (!isoString) {
    return null;
  }

  try {
    // 1. Convertimos el string UTC a un objeto Date.
    // El navegador hace la magia de ajustarlo a la zona horaria local automáticamente.
    const localDate = new Date(isoString);
    const formattedDate = localDate.toLocaleString('es-AR', options);

    // Devolvemos la fecha formateada dentro de una etiqueta <time> semántica,
    // que además incluye la fecha original para accesibilidad y SEO.
    return (
      <time dateTime={isoString}>
        {formattedDate}
      </time>
    );
  } catch (error) {
    // Si por alguna razón la fecha del backend es inválida, mostramos un error
    // en la consola y no rompemos la aplicación.
    console.error("Error al formatear la fecha:", isoString, error);
    return <span className="text-red-500">Fecha inválida</span>;
  }
}