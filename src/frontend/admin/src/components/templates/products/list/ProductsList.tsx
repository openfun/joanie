import * as React from "react";
import { useState } from "react";
import { GridColDef } from "@mui/x-data-grid";
import { defineMessages, useIntl } from "react-intl";
import { useRouter } from "next/router";
import { useDebouncedCallback } from "use-debounce";
import { TableComponent } from "@/components/presentational/table/TableComponent";
import { PATH_ADMIN } from "@/utils/routes/path";
import { Maybe } from "@/types/utils";
import { CustomLink } from "@/components/presentational/link/CustomLink";
import { commonTranslations } from "@/translations/common/commonTranslations";
import { useProducts } from "@/hooks/useProducts/useProducts";
import { Product } from "@/services/api/models/Product";

const messages = defineMessages({
  priceHeader: {
    id: "components.templates.products.list.priceHeader",
    defaultMessage: "price",
    description: "Label for the price header inside the table  ",
  },
  typeHeader: {
    id: "components.templates.products.list.typeHeader",
    defaultMessage: "type",
    description: "Label for the type header inside the table  ",
  },
  title: {
    id: "components.templates.products.list.title",
    defaultMessage: "Title",
    description: "Label for the title header inside the table  ",
  },
});

export function ProductList() {
  const intl = useIntl();
  const { push } = useRouter();
  const [query, setQuery] = useState<Maybe<string>>();
  const products = useProducts({ query });

  const debouncedSetSearch = useDebouncedCallback(setQuery, 300);

  const columns: GridColDef[] = [
    {
      field: "title",
      headerName: intl.formatMessage(messages.title),
      flex: 1,
      renderCell: (cell) => {
        return (
          <CustomLink
            href={PATH_ADMIN.products.edit(cell.row.id)}
            title={intl.formatMessage(commonTranslations.edit)}
          >
            {cell.row.title}
          </CustomLink>
        );
      },
    },
    {
      field: "type",
      headerName: intl.formatMessage(messages.typeHeader),
      maxWidth: 200,
    },
    {
      field: "price",
      headerName: intl.formatMessage(messages.priceHeader),
    },
  ];

  return (
    <TableComponent
      rows={products.items}
      loading={products.states.isLoading || products.states.fetching}
      columns={columns}
      columnBuffer={3}
      onSearch={debouncedSetSearch}
      onEditClick={(product: Product) => {
        if (!product.id) {
          throw new Error("Product id is null");
        }
        push(PATH_ADMIN.products.edit(product.id));
      }}
      onRemoveClick={(product: Product) => {
        products.methods.delete(product.id);
      }}
      getEntityName={(product) => {
        return product.title;
      }}
    />
  );
}
