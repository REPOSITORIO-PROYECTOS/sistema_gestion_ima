import { ProductoAPI } from "./columns";

const API_BASE = "https://sistema-ima.sistemataup.online/api";

export async function fetchAllArticulos(token: string, limit = 200): Promise<ProductoAPI[]> {
    if (!token) return [];

    let pagina = 1;
    const acumulado: ProductoAPI[] = [];

    while (true) {
        const respuesta = await fetch(`${API_BASE}/articulos/obtener_todos?pagina=${pagina}&limite=${limit}`, {
            headers: {
                Authorization: `Bearer ${token}`,
            },
        });

        if (!respuesta.ok) {
            throw new Error(`Fallo al obtener artículos (status ${respuesta.status})`);
        }

        const lote: ProductoAPI[] = await respuesta.json();
        acumulado.push(...lote);

        if (lote.length < limit) {
            break;
        }

        pagina += 1;
    }

    return acumulado;
}
