import { stock } from "@/data/stock.data";
import { DataTable } from "./data-table";
import { columns } from "./columns";

// Traigo datos de acá, modificar despues
async function fetchData() {

    return stock;
}

async function Page() {

    const data = await fetchData();

    return (
        <DataTable columns={columns} data={data} />
    )
}

export default Page;