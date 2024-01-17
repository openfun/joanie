import * as React from "react";
import { GridColDef } from "@mui/x-data-grid";
import { defineMessages, useIntl } from "react-intl";
import { TableComponent } from "@/components/presentational/table/TableComponent";
import { SimpleCard } from "@/components/presentational/card/SimpleCard";
import { usePaginatedTableResource } from "@/components/presentational/table/usePaginatedTableResource";
import { OrderListItem } from "@/services/api/models/Order";
import { useOrders } from "@/hooks/useOrders/useOrders";
import { CustomLink } from "@/components/presentational/link/CustomLink";
import { PATH_ADMIN } from "@/utils/routes/path";
import { commonTranslations } from "@/translations/common/commonTranslations";

const messages = defineMessages({
  id: {
    id: "components.templates.orders.list.id",
    defaultMessage: "ID",
    description: "Label for the id header inside the table",
  },
  organizationTitle: {
    id: "components.templates.orders.list.organizationTitle",
    defaultMessage: "Organization",
    description: "Label for the organization header inside the table",
  },
  product: {
    id: "components.templates.orders.list.product",
    defaultMessage: "Product",
    description: "Label for the product header inside the table",
  },
  owner: {
    id: "components.templates.orders.list.owner",
    defaultMessage: "Owner",
    description: "Label for the owner header inside the table",
  },
  state: {
    id: "components.templates.orders.list.state",
    defaultMessage: "State",
    description: "Label for the state header inside the table",
  },
});

export function OrdersList() {
  const intl = useIntl();
  const paginatedResource = usePaginatedTableResource<OrderListItem>({
    useResource: useOrders,
  });

  const columns: GridColDef[] = [
    {
      field: "product_title",
      headerName: intl.formatMessage(messages.product),
      renderCell: (cell) => {
        return (
          <CustomLink
            href={PATH_ADMIN.orders.view(cell.row.id)}
            title={intl.formatMessage(commonTranslations.view)}
          >
            {cell.row.product_title}
          </CustomLink>
        );
      },
      flex: 1,
    },
    {
      field: "owner_name",
      headerName: intl.formatMessage(messages.owner),
      flex: 1,
    },
    {
      field: "organization_title",
      headerName: intl.formatMessage(messages.organizationTitle),
      flex: 1,
    },
    {
      field: "state",
      headerName: intl.formatMessage(messages.state),
      flex: 1,
    },
  ];

  return (
    <SimpleCard>
      <TableComponent
        {...paginatedResource.tableProps}
        enableEdit={false}
        columns={columns}
        columnBuffer={5}
        getEntityName={(organization) => {
          return organization.title;
        }}
      />
    </SimpleCard>
  );
}
