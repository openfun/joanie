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
import {
  ProductResourceQuery,
  useProducts,
} from "@/hooks/useProducts/useProducts";
import { Product } from "@/services/api/models/Product";
import { usePaginatedTableResource } from "@/components/presentational/table/usePaginatedTableResource";
import { ProductFilers } from "@/components/templates/products/filters/ProductFilters";

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

type Props = DefaultTableProps<Product>;

export function ProductList(props: Props) {
  const intl = useIntl();
  const { push } = useRouter();
  const paginatedResource = usePaginatedTableResource<
    Product,
    ProductResourceQuery
  >({
    useResource: useProducts,
    changeUrlOnPageChange: props.changeUrlOnPageChange,
  });

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
      {...paginatedResource.tableProps}
      {...props}
      filters={<ProductFilers {...paginatedResource.filtersProps} />}
      columns={columns}
      columnBuffer={3}
      onEditClick={(product: Product) => {
        if (!product.id) {
          throw new Error("Product id is null");
        }
        push(PATH_ADMIN.products.edit(product.id));
      }}
      onRemoveClick={(product: Product) => {
        paginatedResource.methods.delete(product.id);
      }}
      onUseAsTemplateClick={(product) => {
        if (product.id === undefined) {
          return;
        }
        push(`${PATH_ADMIN.products.create}?from=${product?.id}`);
      }}
      getEntityName={(product) => {
        return product.title;
      }}
    />
  );
}
