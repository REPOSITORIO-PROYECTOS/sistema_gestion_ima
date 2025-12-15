import type { TicketResponse } from '@/lib/types/mesas';

export const buildTicketHtml = (titulo: string, ticket: TicketResponse, detalles?: TicketResponse['detalles']) => {
  const fecha = new Date(ticket.timestamp).toLocaleString('es-AR');
  const rows = (detalles ?? ticket.detalles)
    .map(
      (d) =>
        `<tr>
          <td style="padding:4px 8px">${d.articulo}</td>
          <td style="padding:4px 8px;text-align:center">${d.cantidad}</td>
          <td style="padding:4px 8px;text-align:right">$${d.precio_unitario.toFixed(2)}</td>
          <td style="padding:4px 8px;text-align:right">$${d.subtotal.toFixed(2)}</td>
        </tr>`
    )
    .join('');
  const total = (detalles ?? ticket.detalles).reduce((acc, d) => acc + d.subtotal, 0);
  return `<!doctype html>
  <html>
    <head>
      <meta charset="utf-8" />
      <title>${titulo} Mesa ${ticket.mesa_numero}</title>
      <style>
        body{font-family:system-ui, -apple-system, Segoe UI, Roboto, Arial;}
        .ticket{max-width:360px;margin:0 auto}
        h1{font-size:16px;margin:0 0 8px}
        .meta{font-size:12px;color:#555}
        table{width:100%;border-collapse:collapse;margin-top:8px}
        tfoot td{font-weight:600;border-top:1px solid #ddd}
      </style>
    </head>
    <body onload="window.print()">
      <div class="ticket">
        <h1>${titulo} Mesa ${ticket.mesa_numero}</h1>
        <div class="meta">${fecha}</div>
        <table>
          <thead>
            <tr>
              <td>Producto</td>
              <td style="text-align:center">Cant.</td>
              <td style="text-align:right">Precio</td>
              <td style="text-align:right">Subtotal</td>
            </tr>
          </thead>
          <tbody>
            ${rows}
          </tbody>
          <tfoot>
            <tr>
              <td colspan="3" style="padding:6px 8px">Total</td>
              <td style="padding:6px 8px;text-align:right">$${total.toFixed(2)}</td>
            </tr>
          </tfoot>
        </table>
      </div>
    </body>
  </html>`;
};

export const printHtml = (html: string) => {
  const w = window.open('', '_blank');
  if (w) {
    w.document.write(html);
    w.document.close();
  }
};
