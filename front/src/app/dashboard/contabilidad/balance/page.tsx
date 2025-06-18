
import { DataTable } from "./data-table";
import { columns } from "./columns";
import { balance } from "@/data/balance.data";

async function fetchData() {

    return balance;
}

async function Balance() {

    const data = await fetchData();

    return (

        <div>
            <DataTable columns={columns} data={data} />
        </div>
    )
}

export default Balance;