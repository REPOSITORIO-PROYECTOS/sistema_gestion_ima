import { v4 as uuidV4 } from "uuid";
import { uniqueNamesGenerator, Config, names } from "unique-names-generator";

const config: Config = {
  dictionaries: [names],
};

/* TIPO DE PRODUCTO QUE VENDE EL PROVEEDOR */
export type ProductosProveedor = {
  id: string;
  producto: string;
  proveedor: string;
  cantidad: number;
  costo: number;
  fecha: Date;
};

/* LISTA DE PRODUCTOS */
const listaProductos = [
  "Cajón de Naranja", "Cajón de Manzana", "Cajón de Durazno", 
  "Pulpa de Naranja", "Pulpa de Manzana", "Pulpa de Durazno",
  "Naranja Disecada", "Manzana Disecada", "Durazno Disecado",
];


/* PRODUCTO ALEATORIO */
const randomProducto = () => {
  return listaProductos[Math.floor(Math.random() * listaProductos.length)];
};

/* GENERADOR DE DATOS STOCK */
export const productosProveedor: ProductosProveedor[] = Array.from({ length: 50 }, () => {

  const randomName = uniqueNamesGenerator(config);
  
    return {
      id: uuidV4(),
      producto: randomProducto(),
      proveedor: randomName,
      cantidad: Math.floor(Math.random() * 100) + 1,
      costo: parseFloat((Math.random() * 10000).toFixed(2)),
      fecha: new Date(Date.now() - Math.floor(Math.random() * 10000000000)),
    };
});
