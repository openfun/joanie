import { GridColDef } from "@mui/x-data-grid";
import { render, screen } from "@testing-library/react";
import { IntlProvider } from "react-intl";
import { TableComponent } from "@/components/presentational/table/TableComponent";

describe("<TableComponent/>", () => {
  it("renders a TableComponent component ", async () => {
    const data = [
      { id: "1", lastName: "Doe", firstName: "John" },
      { id: "2", lastName: "Oed", firstName: "Nohj" },
    ];
    const columns: GridColDef[] = [
      {
        field: "lastName",
        headerName: "Last name",
      },
      {
        field: "firstName",
        headerName: "First name",
      },
    ];

    render(
      <IntlProvider locale="en">
        <TableComponent rows={data} columns={columns} />
      </IntlProvider>
    );

    await screen.findByText("Last name");
    screen.getByText("First name");
    screen.getByText("John");
    screen.getByText("Nohj");
  });
});
