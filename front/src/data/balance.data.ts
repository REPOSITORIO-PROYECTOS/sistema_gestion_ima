import { v4 as uuidV4 } from "uuid";
import { uniqueNamesGenerator, Config, names } from "unique-names-generator";

/* CONFIGURACIÓN PARA NOMBRES ALEATORIOS */
const config: Config = {
  dictionaries: [names],
};

/* TIPOS DE DATOS */
export type TipoOperacion = "Compra" | "Venta";
export type TipoUsuario = "Cliente" | "Proveedor";

/* TIPO DE BALANCE */
export type Balance = {
  id: string;
  producto: string;
  cantidad: number;
  operacion: TipoOperacion;
  tipoUsuario: TipoUsuario;
  usuario: string;
  costo: number;
  fecha: Date;
};

/* LISTA DE PRODUCTOS SEPARADOS POR OPERACIÓN */
const productosVenta = [
  "Jugo Naranja 10ml", "Jugo Naranja 30ml", "Jugo Naranja 50ml",
  "Jugo Durazno 10ml", "Jugo Durazno 30ml", "Jugo Durazno 50ml",
  "Jugo Multifruta 10ml", "Jugo Multifruta 30ml", "Jugo Multifruta 50ml",
];

const productosCompra = [
  "Cajón de Naranja", "Cajón de Manzana", "Cajón de Durazno",
  "Pulpa de Naranja", "Pulpa de Manzana", "Pulpa de Durazno",
  "Naranja Disecada", "Manzana Disecada", "Durazno Disecado",
];

/* PRODUCTO ALEATORIO Y TIPO DE OPERACIÓN */
const randomProductoYOperacion = (): { producto: string; operacion: TipoOperacion; tipoUsuario: TipoUsuario } => {
  const esVenta = Math.random() > 0.5;
  const productos = esVenta ? productosVenta : productosCompra;
  return {
    producto: productos[Math.floor(Math.random() * productos.length)],
    operacion: esVenta ? "Venta" : "Compra",
    tipoUsuario: esVenta ? "Cliente" : "Proveedor",
  };
};

/* GENERADOR DE DATOS DE BALANCE */
export const balance: Balance[] = Array.from({ length: 50 }, () => {
  const nombreUsuario = uniqueNamesGenerator(config);
  const { producto, operacion, tipoUsuario } = randomProductoYOperacion();

  return {
    id: uuidV4(),
    producto,
    cantidad: Math.floor(Math.random() * 100) + 1,
    operacion,
    tipoUsuario,
    usuario: nombreUsuario,
    costo: parseFloat((Math.random() * 10000).toFixed(2)),
    fecha: new Date(Date.now() - Math.floor(Math.random() * 10000000000)),
  };
});
