"use client"

import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Printer, Download } from 'lucide-react';
import type { TicketResponse } from '@/lib/types/mesas';

interface TicketModalProps {
  ticket: TicketResponse | null;
  isOpen: boolean;
  onClose: () => void;
}

export function TicketModal({ ticket, isOpen, onClose }: TicketModalProps) {
  const buildHtml = () => {
    if (!ticket) return '';
    const fecha = new Date(ticket.timestamp).toLocaleString('es-AR');
    const rows = ticket.detalles
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
    return `<!doctype html>
    <html>
      <head>
        <meta charset="utf-8" />
        <title>Ticket Mesa ${ticket.mesa_numero}</title>
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
          <h1>Ticket Mesa ${ticket.mesa_numero}</h1>
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
                <td style="padding:6px 8px;text-align:right">$${ticket.total.toFixed(2)}</td>
              </tr>
            </tfoot>
          </table>
        </div>
      </body>
    </html>`;
  };

  const handlePrint = () => {
    if (!ticket) return;
    const html = buildHtml();
    const printWindow = window.open('', '_blank');
    if (printWindow) {
      printWindow.document.write(html);
      printWindow.document.close();
    }
  };

  const handleDownload = () => {
    if (!ticket) return;
    const html = buildHtml();
    const blob = new Blob([html], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `ticket_mesa_${ticket.mesa_numero}_${new Date().toISOString().split('T')[0]}.html`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  if (!ticket) return null;

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Ticket de Mesa {ticket.mesa_numero}</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          <div className="border rounded-lg p-4 bg-white">
            <div className="space-y-2">
              <div className="text-sm text-gray-600">
                {new Date(ticket.timestamp).toLocaleString('es-AR')}
              </div>
              <div className="text-sm">
                {ticket.detalles.map((d, idx) => (
                  <div key={idx} className="flex justify-between gap-2 py-1">
                    <span className="flex-1">{d.articulo}</span>
                    <span className="w-12 text-center">{d.cantidad}</span>
                    <span className="w-24 text-right">${d.precio_unitario.toFixed(2)}</span>
                    <span className="w-24 text-right font-medium">${d.subtotal.toFixed(2)}</span>
                  </div>
                ))}
              </div>
              <div className="flex justify-end border-t pt-2">
                <span className="font-semibold">Total: ${ticket.total.toFixed(2)}</span>
              </div>
            </div>
          </div>

          {/* Acciones */}
          <div className="flex gap-2 justify-end">
            <Button variant="outline" onClick={handleDownload}>
              <Download className="h-4 w-4 mr-2" />
              Descargar
            </Button>
            <Button onClick={handlePrint}>
              <Printer className="h-4 w-4 mr-2" />
              Imprimir
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
