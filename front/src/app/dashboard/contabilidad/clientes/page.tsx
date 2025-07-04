import { productosCliente } from "@/data/prodcliente.data";
import { DataTable } from "./data-table";
import { columns } from "./columns";

async function fetchData() {

    return productosCliente;
}

async function Clientes() {

    const data = await fetchData();

    return (

        <div>
            <DataTable columns={columns} data={data} />
        </div>
    )
}

export default Clientes;