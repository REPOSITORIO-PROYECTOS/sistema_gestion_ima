import { API_CONFIG } from "@/lib/api-config";
import { toast } from "sonner";

export async function imprimirArqueoCaja(
  idSesion: number,
  token: string,
): Promise<void> {
  toast.info("Generando ticket, por favor espere...");

  const url = `${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.CAJA_TICKET_CIERRE(idSesion)}`;

  const res = await fetch(url, {
    headers: { Authorization: `Bearer ${token}` },
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(
      (errorData as { detail?: string }).detail ||
        `El servidor respondió con un error ${res.status}`,
    );
  }

  const blob = await res.blob();

  if (blob.size === 0) {
    throw new Error("El servidor devolvió un archivo vacío.");
  }
  if (blob.type !== "application/pdf") {
    throw new Error(
      `El servidor devolvió un tipo de archivo incorrecto (${blob.type}), se esperaba un PDF.`,
    );
  }

  const fileURL = URL.createObjectURL(blob);
  const newWindow = window.open(fileURL, "_blank");

  if (!newWindow) {
    URL.revokeObjectURL(fileURL);
    throw new Error(
      "El navegador bloqueó la apertura de la nueva pestaña. Revisá la configuración de pop-ups.",
    );
  }

  setTimeout(() => URL.revokeObjectURL(fileURL), 100);
}
