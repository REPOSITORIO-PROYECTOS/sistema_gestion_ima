import { productosProveedor } from "@/data/prodproveedor.data";
import { DataTable } from "./data-table";
import { columns } from "./columns";

async function fetchData() {

    return productosProveedor;
}

async function Proveedores() {

    const data = await fetchData();

    return (

        <div>
            <DataTable columns={columns} data={data} />
        </div>
    )
}

export default Proveedores;