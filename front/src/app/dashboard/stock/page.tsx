import { stock } from "@/data/stock.data";
import { DataTable } from "./data-table";
import { columns } from "./columns";

async function fetchData() {

    return stock;
}

async function Page() {

    const data = await fetchData();

    return (

        <div>
            <DataTable columns={columns} data={data} />
        </div>
    )
}

export default Page;