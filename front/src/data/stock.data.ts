import { v4 as uuidV4 } from "uuid";

/* TIPO DE DATO STOCK */
export type Stock = {
  id: string;
  producto: string;
  cantidad: number;
  costo: number;
  ubicacion: "Depósito A" | "Depósito B" | "Sucursal Centro" | "Sucursal Norte";
  fecha: Date;
};

/* LISTA DE PRODUCTOS */
const listaProductos = [
  "Jugo Naranja 10ml", "Jugo Naranja 30ml", "Jugo Naranja 50ml",
  "Jugo Durazno 10ml", "Jugo Durazno 30ml", "Jugo Durazno 50ml",
  "Jugo Multifruta 10ml", "Jugo Multifruta 30ml", "Jugo Multifruta 50ml"
];

/* UBICACIONES FALSAS */
const randomUbicacion = () => {
  const ubicaciones = ["Depósito A", "Depósito B", "Sucursal Centro", "Sucursal Norte"] as const;
  return ubicaciones[Math.floor(Math.random() * ubicaciones.length)];
};

/* PRODUCTO ALEATORIO */
const randomProducto = () => {
  return listaProductos[Math.floor(Math.random() * listaProductos.length)];
};

/* GENERADOR DE DATOS STOCK */
export const stock: Stock[] = Array.from({ length: 50 }, () => {
  return {
    id: uuidV4(),
    producto: randomProducto(),
    cantidad: Math.floor(Math.random() * 100) + 1,
    costo: parseFloat((Math.random() * 10000).toFixed(2)),
    ubicacion: randomUbicacion(),
    fecha: new Date(Date.now() - Math.floor(Math.random() * 10000000000)),
  };
});
