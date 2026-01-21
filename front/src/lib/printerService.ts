import type { TicketResponse } from '@/lib/types/mesas';

export const buildTicketHtml = (titulo: string, ticket: TicketResponse, detalles?: TicketResponse['detalles']) => {
  const isComanda = titulo.toLowerCase().includes('comanda') || titulo.toLowerCase().includes('pedido');
  const fecha = new Date(ticket.timestamp).toLocaleString('es-AR');
  const items = detalles ?? ticket.detalles;

  if (isComanda) {
    // Formato Comanda (55mm, sin precios, solo operativo)
    const rows = items.map(d => `
      <div style="border-bottom: 1px dashed #000; padding: 5px 0;">
        <div style="display:flex; justify-content:space-between; align-items: flex-start; font-weight:bold; font-size:14px;">
          <span style="flex: 1; margin-right: 5px;">${d.articulo}</span>
          <span style="white-space: nowrap;">x ${d.cantidad}</span>
        </div>
        ${d.observacion ? `<div style="font-size:12px; font-weight:bold; margin-top:2px; padding-left: 5px;">** ${d.observacion} **</div>` : ''}
      </div>
    `).join('');

    return `<!doctype html>
    <html>
      <head>
        <meta charset="utf-8" />
        <title>${titulo}</title>
        <style>
          body { font-family: 'Courier New', monospace; margin: 0; padding: 0; background: #fff; }
          .ticket { width: 55mm; margin: 0; padding: 2mm; box-sizing: border-box; }
          h1 { font-size: 16px; margin: 0 0 5px; text-align: center; text-transform: uppercase; }
          .meta { font-size: 12px; margin-bottom: 10px; border-bottom: 2px solid #000; padding-bottom: 5px; }
          .meta div { margin-bottom: 2px; }
          .items { margin-top: 5px; }
        </style>
      </head>
      <body onload="window.print()">
        <div class="ticket">
          <h1>${titulo}</h1>
          <div class="meta">
            <div>MESA: <span style="font-size:18px; font-weight:bold">${ticket.mesa_numero}</span></div>
            <div>MOZO: ${ticket.mozo || 'S/A'}</div>
            <div>FECHA: ${fecha}</div>
          </div>
          <div class="items">
            ${rows}
          </div>
          <div style="margin-top:10px; text-align:center; font-size:12px; border-top: 2px solid #000; padding-top:5px;">
            --- FIN ---
          </div>
        </div>
      </body>
    </html>`;
  }

  // Formato Ticket/Pre-cuenta (Estándar, con precios)
  const rows = items
    .map(
      (d) =>
        `<tr>
          <td style="padding:4px 8px">
            ${d.articulo}
            ${d.observacion ? `<div style="font-size:10px;font-style:italic;color:#555">(${d.observacion})</div>` : ''}
          </td>
          <td style="padding:4px 8px;text-align:center">${d.cantidad}</td>
          <td style="padding:4px 8px;text-align:right">$${d.precio_unitario.toFixed(2)}</td>
          <td style="padding:4px 8px;text-align:right">$${d.subtotal.toFixed(2)}</td>
        </tr>`
    )
    .join('');
  const total = items.reduce((acc, d) => acc + d.subtotal, 0);

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
