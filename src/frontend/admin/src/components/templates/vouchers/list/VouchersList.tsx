import * as React from "react";
import { GridColDef } from "@mui/x-data-grid";
import { defineMessages, useIntl } from "react-intl";
import CopyAllIcon from "@mui/icons-material/CopyAll";
import {
  DefaultTableProps,
  TableComponent,
} from "@/components/presentational/table/TableComponent";
import { PATH_ADMIN } from "@/utils/routes/path";
import { CustomLink } from "@/components/presentational/link/CustomLink";
import { commonTranslations } from "@/translations/common/commonTranslations";
import { usePaginatedTableResource } from "@/components/presentational/table/usePaginatedTableResource";
import { Voucher, VoucherQuery } from "@/services/api/models/Voucher";
import { useVouchers } from "@/hooks/useVouchers/useVouchers";
import { VoucherFilters } from "@/components/templates/vouchers/filters/VoucherFilters";
import { getDiscountLabel } from "@/services/api/models/Discount";
import { useCopyToClipboard } from "@/hooks/useCopyToClipboard";

const messages = defineMessages({
  codeHeader: {
    id: "components.templates.vouchers.list.codeHeader",
    defaultMessage: "Code",
    description: "Label for the code header inside the table",
  },
  isActiveHeader: {
    id: "components.templates.vouchers.list.isActiveHeader",
    defaultMessage: "Is active",
    description: "Label for the is active header inside the table",
  },
  discountHeader: {
    id: "components.templates.vouchers.list.discountHeader",
    defaultMessage: "Discount",
    description: "Label for the discount header inside the table",
  },
  multipleUseHeader: {
    id: "components.templates.vouchers.list.multipleUseHeader",
    defaultMessage: "Multiple use",
    description: "Label for the multiple use header inside the table",
  },
  multipleUsersHeader: {
    id: "components.templates.vouchers.list.multipleUsersHeader",
    defaultMessage: "Multiple users",
    description: "Label for the multiple users header inside the table",
  },
  ordersCountHeader: {
    id: "components.templates.vouchers.list.ordersCountHeader",
    defaultMessage: "Orders count",
    description: "Label for the orders count header inside the table",
  },
  copyCode: {
    id: "components.templates.vouchers.list.copyCode",
    defaultMessage: "Copy code",
    description: "Label for the copy code button inside the table",
  },
});

type Props = DefaultTableProps<Voucher>;

export function VouchersList(props: Props) {
  const intl = useIntl();
  const copyToClipboard = useCopyToClipboard();

  const paginatedResource = usePaginatedTableResource<Voucher, VoucherQuery>({
    useResource: useVouchers,
    changeUrlOnPageChange: props.changeUrlOnPageChange,
  });

  const columns: GridColDef[] = [
    {
      field: "code",
      headerName: intl.formatMessage(messages.codeHeader),
      flex: 4,
      renderCell: (cell) => (
        <CustomLink
          href={PATH_ADMIN.vouchers.edit(cell.row.id)}
          title={intl.formatMessage(commonTranslations.edit)}
        >
          {cell.row.code}
        </CustomLink>
      ),
    },
    {
      field: "discount",
      headerName: intl.formatMessage(messages.discountHeader),
      flex: 1,
      renderCell: (cell) => getDiscountLabel(cell.row.discount),
    },
    {
      field: "is_active",
      headerName: intl.formatMessage(messages.isActiveHeader),
      flex: 1,
      renderCell: (cell) => (cell.row.is_active ? "✓" : "—"),
    },
    {
      field: "multiple_use",
      headerName: intl.formatMessage(messages.multipleUseHeader),
      flex: 1,
      renderCell: (cell) => (cell.row.multiple_use ? "✓" : "—"),
    },
    {
      field: "multiple_users",
      headerName: intl.formatMessage(messages.multipleUsersHeader),
      flex: 1,
      renderCell: (cell) => (cell.row.multiple_users ? "✓" : "—"),
    },
    {
      field: "orders_count",
      headerName: intl.formatMessage(messages.ordersCountHeader),
      flex: 1,
    },
  ];

  return (
    <TableComponent
      {...paginatedResource.tableProps}
      {...props}
      filters={<VoucherFilters {...paginatedResource.filtersProps} />}
      columns={columns}
      columnBuffer={3}
      getOptions={(voucher) => {
        const { code } = voucher;

        return [
          {
            mainLabel: intl.formatMessage(messages.copyCode),
            icon: <CopyAllIcon fontSize="small" />,
            onClick: () => copyToClipboard(code),
          },
        ];
      }}
      onRemoveClick={(voucher: Voucher) => {
        paginatedResource.methods.delete(voucher.id);
      }}
      getEntityName={(voucher) => voucher.code}
    />
  );
}
