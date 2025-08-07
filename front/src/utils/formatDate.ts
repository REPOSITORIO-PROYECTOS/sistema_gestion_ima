
// Funcion para formatear las fechas y horas a horario Argentino
// Convierte string ISO (UTC) a fecha/hora local argentina
export function formatDateArgentina(fecha: string): string {
  const fechaUTC = fecha.endsWith("Z") ? fecha : `${fecha}Z`;
  return new Date(fechaUTC).toLocaleString("es-AR", {
    timeZone: "America/Argentina/Buenos_Aires",
    hour12: false,
    dateStyle: "short",
    timeStyle: "short",
  });
}
