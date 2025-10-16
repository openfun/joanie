import * as React from "react";
import { GridColDef } from "@mui/x-data-grid";
import { defineMessages, useIntl } from "react-intl";
import {
  DefaultTableProps,
  TableComponent,
} from "@/components/presentational/table/TableComponent";
import { SimpleCard } from "@/components/presentational/card/SimpleCard";
import { usePaginatedTableResource } from "@/components/presentational/table/usePaginatedTableResource";
import { BatchOrderListItem } from "@/services/api/models/BatchOrder";
import {
  BatchOrderListQuery,
  useBatchOrders,
} from "@/hooks/useBatchOrders/useBatchOrders";
import { CustomLink } from "@/components/presentational/link/CustomLink";
import { PATH_ADMIN } from "@/utils/routes/path";
import { commonTranslations } from "@/translations/common/commonTranslations";
import { formatShortDate } from "@/utils/dates";
import { BatchOrderFilters } from "@/components/templates/batch-orders/filters/BatchOrderFilters";

const messages = defineMessages({
  product: {
    id: "components.templates.orders.list.product",
    defaultMessage: "Product",
    description: "Label for the product header inside the table",
  },
  companyName: {
    id: "components.templates.batchOrders.list.companyName",
    defaultMessage: "Company",
    description: "Label for the company header inside the table",
  },
  organizationTitle: {
    id: "components.templates.batchOrders.list.organizationTitle",
    defaultMessage: "Organization",
    description: "Label for the organization header inside the table",
  },
  ownerName: {
    id: "components.templates.batchOrders.list.ownerName",
    defaultMessage: "Owner",
    description: "Label for the owner header inside the table",
  },
  nbSeats: {
    id: "components.templates.batchOrders.list.nbSeats",
    defaultMessage: "Seats",
    description: "Label for the number of seats header inside the table",
  },
  state: {
    id: "components.templates.batchOrders.list.state",
    defaultMessage: "State",
    description: "Label for the state header inside the table",
  },
  createdOn: {
    id: "components.templates.batchOrders.list.createdOn",
    defaultMessage: "Created on",
    description: "Label for the created on header inside the table",
  },
  updatedOn: {
    id: "components.templates.batchOrders.list.updatedOn",
    defaultMessage: "Updated on",
    description: "Label for the updated on header inside the table",
  },
  total: {
    id: "components.templates.batchOrders.list.total",
    defaultMessage: "Total",
    description: "Label for the total header inside the table",
  },
});

type Props = DefaultTableProps<BatchOrderListItem>;

export function BatchOrdersList(props: Props) {
  const intl = useIntl();

  const paginatedResource = usePaginatedTableResource<
    BatchOrderListItem,
    BatchOrderListQuery
  >({
    useResource: useBatchOrders,
    changeUrlOnPageChange: props.changeUrlOnPageChange,
  });

  const columns: GridColDef[] = [
    {
      field: "product_title",
      headerName: intl.formatMessage(messages.product),
      renderCell: (cell) => {
        return (
          <CustomLink
            href={PATH_ADMIN.batch_orders.view(cell.row.id)}
            title={intl.formatMessage(commonTranslations.view)}
          >
            {cell.row.product_title}
          </CustomLink>
        );
      },
      flex: 1,
    },
    {
      field: "company_name",
      headerName: intl.formatMessage(messages.companyName),
      flex: 1,
    },
    {
      field: "owner_name",
      headerName: intl.formatMessage(messages.ownerName),
      flex: 1,
    },
    {
      field: "organization_title",
      headerName: intl.formatMessage(messages.organizationTitle),
      flex: 1,
    },
    {
      field: "nb_seats",
      headerName: intl.formatMessage(messages.nbSeats),
      flex: 1,
    },
    {
      field: "state",
      headerName: intl.formatMessage(messages.state),
      flex: 1,
    },
    {
      field: "created_on",
      headerName: intl.formatMessage(messages.createdOn),
      flex: 1,
      valueGetter: (value, row) => formatShortDate(row.created_on),
    },
    {
      field: "updated_on",
      headerName: intl.formatMessage(messages.updatedOn),
      flex: 1,
      valueGetter: (value, row) => formatShortDate(row.updated_on),
    },
    {
      field: "total",
      headerName: intl.formatMessage(messages.total),
      flex: 1,
      valueGetter: (value, row) => {
        return row.total ? `${row.total} ${row.total_currency}` : "-";
      },
    },
  ];

  return (
    <SimpleCard>
      <TableComponent
        {...paginatedResource.tableProps}
        {...props}
        filters={<BatchOrderFilters {...paginatedResource.filtersProps} />}
        enableEdit={false}
        columns={columns}
        columnBuffer={5}
        getEntityName={(batch) => {
          return batch.company_name;
        }}
      />
    </SimpleCard>
  );
}
