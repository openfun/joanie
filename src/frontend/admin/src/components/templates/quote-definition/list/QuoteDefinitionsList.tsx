import * as React from "react";
import { defineMessages, useIntl } from "react-intl";
import { useRouter } from "next/router";
import { GridColDef } from "@mui/x-data-grid";
import {
  DefaultTableProps,
  TableComponent,
} from "@/components/presentational/table/TableComponent";
import { PATH_ADMIN } from "@/utils/routes/path";
import { CustomLink } from "@/components/presentational/link/CustomLink";
import { commonTranslations } from "@/translations/common/commonTranslations";
import { SimpleCard } from "@/components/presentational/card/SimpleCard";
import {
  QuoteDefinitionResourceQuery,
  useQuoteDefinitions,
} from "@/hooks/useQuoteDefinitions/useQuoteDefinitions";
import { QuoteDefinition } from "@/services/api/models/QuoteDefinition";
import { usePaginatedTableResource } from "@/components/presentational/table/usePaginatedTableResource";
import { QuoteDefinitionFilters } from "@/components/templates/quote-definition/filters/QuoteDefinitionFilters";

const messages = defineMessages({
  languageHeader: {
    id: "components.templates.quoteDefinitions.list.languageHeader",
    defaultMessage: "Language",
    description: "Label for the language header inside the table  ",
  },
  titleHeader: {
    id: "components.templates.quoteDefinitions.list.titleHeader",
    defaultMessage: "Title",
    description: "Label for the title header inside the table  ",
  },
});

type Props = DefaultTableProps<QuoteDefinition>;

export function QuoteDefinitionsList(props: Props) {
  const intl = useIntl();
  const paginatedResource = usePaginatedTableResource<
    QuoteDefinition,
    QuoteDefinitionResourceQuery
  >({
    useResource: useQuoteDefinitions,
    changeUrlOnPageChange: props.changeUrlOnPageChange,
  });

  const { push } = useRouter();

  const columns: GridColDef<QuoteDefinition>[] = [
    {
      field: "title",
      headerName: intl.formatMessage(messages.titleHeader),
      flex: 1,

      renderCell: (cell) => {
        return (
          <CustomLink
            href={PATH_ADMIN.quote_definition.edit(cell.row.id)}
            title={intl.formatMessage(commonTranslations.edit)}
          >
            {cell.row.title}
          </CustomLink>
        );
      },
    },
    {
      field: "language",
      headerName: intl.formatMessage(messages.languageHeader),
      minWidth: 400,
    },
  ];

  return (
    <SimpleCard>
      <TableComponent
        {...paginatedResource.tableProps}
        {...props}
        columns={columns}
        filters={<QuoteDefinitionFilters {...paginatedResource.filtersProps} />}
        columnBuffer={3}
        onEditClick={(quotesDefinition: QuoteDefinition) => {
          if (quotesDefinition.id === undefined) {
            return;
          }
          push(PATH_ADMIN.quote_definition.edit(quotesDefinition.id));
        }}
        onUseAsTemplateClick={(quoteDefinition) => {
          if (quoteDefinition.id === undefined) {
            return;
          }
          push(
            `${PATH_ADMIN.quote_definition.create}?from=${quoteDefinition?.id}`,
          );
        }}
        getEntityName={(quotesDefinition) => {
          return quotesDefinition.name;
        }}
        onRemoveClick={(quoteDefinition: QuoteDefinition) => {
          paginatedResource.methods.delete(quoteDefinition.id);
        }}
      />
    </SimpleCard>
  );
}
