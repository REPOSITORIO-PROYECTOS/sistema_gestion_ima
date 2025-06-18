


/* ESTO NO VA, LOS DATOS VIENEN DE AFUERA, SOLO DE EJEMPLO */




import { v4 as uuidV4 } from "uuid";
import { uniqueNamesGenerator, Config, names } from "unique-names-generator";

const config: Config = {
  dictionaries: [names],
};

/* TIPO DE PRODUCTOS QUE SE VENDEN A LOS CLIENTES */
export type ProductosCliente = {
  id: string;
  producto: string;
  cliente: string; 
  cantidad: number;
  costo: number;
  fecha: Date;
};

/* LISTA DE PRODUCTOS */
const listaProductos = [
  "Jugo Naranja 10ml", "Jugo Naranja 30ml", "Jugo Naranja 50ml",
  "Jugo Durazno 10ml", "Jugo Durazno 30ml", "Jugo Durazno 50ml",
  "Jugo Multifruta 10ml", "Jugo Multifruta 30ml", "Jugo Multifruta 50ml"
];

/* PRODUCTO ALEATORIO */
const randomProducto = () => {
  return listaProductos[Math.floor(Math.random() * listaProductos.length)];
};

/* GENERADOR DE DATOS STOCK */
export const productosCliente: ProductosCliente[] = Array.from({ length: 50 }, () => {

  const randomName = uniqueNamesGenerator(config);

  return {
    id: uuidV4(),
    producto: randomProducto(),
    cliente: randomName,
    cantidad: Math.floor(Math.random() * 100) + 1,
    costo: parseFloat((Math.random() * 10000).toFixed(2)),
    fecha: new Date(Date.now() - Math.floor(Math.random() * 10000000000)),
  };
});
