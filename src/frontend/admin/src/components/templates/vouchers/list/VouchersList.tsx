import * as React from "react";
import { GridColDef } from "@mui/x-data-grid";
import { defineMessages, useIntl } from "react-intl";
import { useRouter } from "next/router";
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

const messages = defineMessages({
  codeHeader: {
    id: "components.templates.vouchers.list.codeHeader",
    defaultMessage: "Code",
    description: "Label for the code header inside the table",
  },
  offeringRuleHeader: {
    id: "components.templates.vouchers.list.offeringRuleHeader",
    defaultMessage: "Offering rule",
    description: "Label for the offering rule header inside the table",
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
});

type Props = DefaultTableProps<Voucher>;

export function VouchersList(props: Props) {
  const intl = useIntl();
  const { push } = useRouter();

  const paginatedResource = usePaginatedTableResource<Voucher, VoucherQuery>({
    useResource: useVouchers,
    changeUrlOnPageChange: props.changeUrlOnPageChange,
  });

  const columns: GridColDef[] = [
    {
      field: "code",
      headerName: intl.formatMessage(messages.codeHeader),
      flex: 1,
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
    },
    {
      field: "multiple_use",
      headerName: intl.formatMessage(messages.multipleUseHeader),
      maxWidth: 180,
      align: "center",
      headerAlign: "center",
      renderCell: (cell) => (cell.row.multiple_use ? "✓" : "—"),
    },
    {
      field: "multiple_users",
      headerName: intl.formatMessage(messages.multipleUsersHeader),
      maxWidth: 180,
      align: "center",
      headerAlign: "center",
      renderCell: (cell) => (cell.row.multiple_users ? "✓" : "—"),
    },
  ];

  return (
    <TableComponent
      {...paginatedResource.tableProps}
      {...props}
      filters={<VoucherFilters {...paginatedResource.filtersProps} />}
      columns={columns}
      columnBuffer={3}
      onEditClick={(voucher: Voucher) => {
        if (!voucher.id) {
          throw new Error("Voucher id is null");
        }
        push(PATH_ADMIN.vouchers.edit(voucher.id));
      }}
      onRemoveClick={(voucher: Voucher) => {
        paginatedResource.methods.delete(voucher.id);
      }}
      onUseAsTemplateClick={(voucher) => {
        if (voucher.id === undefined) {
          return;
        }
        push(`${PATH_ADMIN.vouchers.create}?from=${voucher.id}`);
      }}
      getEntityName={(voucher) => voucher.code}
    />
  );
}
