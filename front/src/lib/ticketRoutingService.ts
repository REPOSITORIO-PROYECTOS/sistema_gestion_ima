import type { TicketResponse } from '@/lib/types/mesas';
import { buildTicketHtml, printHtml } from '@/lib/printerService';

const esDeBar = (categoria?: string | null, descripcion?: string) => {
  const text = `${(categoria || '').toLowerCase()} ${(descripcion || '').toLowerCase()}`;
  return /bebida|trago|bar|vino|cerveza|gaseosa|agua/.test(text);
};

export const routeToDepartments = (ticket: TicketResponse) => {
  const cocina = ticket.detalles.filter(d => !esDeBar(d.categoria, d.articulo));
  const bar = ticket.detalles.filter(d => esDeBar(d.categoria, d.articulo));

  if (cocina.length > 0) {
    const htmlCocina = buildTicketHtml('Comanda Cocina', ticket, cocina);
    printHtml(htmlCocina);
  }
  if (bar.length > 0) {
    const htmlBar = buildTicketHtml('Comanda Bar', ticket, bar);
    printHtml(htmlBar);
  }
};
