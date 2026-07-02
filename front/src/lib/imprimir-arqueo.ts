import { API_CONFIG } from "@/lib/api-config";
import { toast } from "sonner";

function esPdfBlob(blob: Blob): boolean {
  if (blob.type === "application/pdf" || blob.type === "application/octet-stream") {
    return true;
  }
  return blob.type === "" || blob.type === "binary/octet-stream";
}

function abrirPdfEnNuevaPestana(blob: Blob, printWindow?: Window | null): void {
  const fileURL = URL.createObjectURL(blob);

  if (printWindow && !printWindow.closed) {
    printWindow.location.href = fileURL;
    setTimeout(() => URL.revokeObjectURL(fileURL), 60_000);
    return;
  }

  const newWindow = window.open(fileURL, "_blank");
  if (!newWindow) {
    const link = document.createElement("a");
    link.href = fileURL;
    link.download = `cierre_caja_${Date.now()}.pdf`;
    link.click();
    setTimeout(() => URL.revokeObjectURL(fileURL), 60_000);
    toast.message("Se descargó el PDF del arqueo.", {
      description: "Si no se abrió solo, revisá la carpeta de descargas.",
    });
    return;
  }

  setTimeout(() => URL.revokeObjectURL(fileURL), 60_000);
}

/** Abrir en el mismo click del usuario evita que el navegador bloquee el PDF tras awaits. */
export function prepararVentanaImpresionCaja(): Window | null {
  return window.open("about:blank", "_blank");
}

export async function imprimirArqueoCaja(
  idSesion: number,
  token: string,
  printWindow?: Window | null,
): Promise<void> {
  toast.info("Generando ticket, por favor espere...");

  const url = `${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.CAJA_TICKET_CIERRE(idSesion)}`;

  try {
    const res = await fetch(url, {
      headers: { Authorization: `Bearer ${token}` },
    });

    if (!res.ok) {
      printWindow?.close();
      const errorData = await res.json().catch(() => ({}));
      throw new Error(
        (errorData as { detail?: string }).detail ||
          `El servidor respondió con un error ${res.status}`,
      );
    }

    const blob = await res.blob();

    if (blob.size === 0) {
      printWindow?.close();
      throw new Error("El servidor devolvió un archivo vacío.");
    }
    if (!esPdfBlob(blob)) {
      printWindow?.close();
      throw new Error(
        `El servidor devolvió un tipo de archivo incorrecto (${blob.type}), se esperaba un PDF.`,
      );
    }

    abrirPdfEnNuevaPestana(blob, printWindow);
  } catch (error) {
    printWindow?.close();
    throw error;
  }
}
