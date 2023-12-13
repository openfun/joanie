import * as React from "react";
import { defineMessages, useIntl } from "react-intl";
import { useRouter } from "next/router";
import { GridColDef } from "@mui/x-data-grid";
import { TableComponent } from "@/components/presentational/table/TableComponent";
import { PATH_ADMIN } from "@/utils/routes/path";
import { CustomLink } from "@/components/presentational/link/CustomLink";
import { commonTranslations } from "@/translations/common/commonTranslations";
import { SimpleCard } from "@/components/presentational/card/SimpleCard";
import { useContractDefinitions } from "@/hooks/useContractDefinitions/useContractDefinitions";
import { ContractDefinition } from "@/services/api/models/ContractDefinition";
import { usePaginatedTableResource } from "@/components/presentational/table/usePaginatedTableResource";

const messages = defineMessages({
  languageHeader: {
    id: "components.templates.contractsDefinitions.list.languageHeader",
    defaultMessage: "Language",
    description: "Label for the language header inside the table  ",
  },
  titleHeader: {
    id: "components.templates.contractsDefinitions.list.titleHeader",
    defaultMessage: "Title",
    description: "Label for the title header inside the table  ",
  },
});

export function ContractsDefinitionsList() {
  const intl = useIntl();
  const paginatedResource = usePaginatedTableResource<ContractDefinition>({
    useResource: useContractDefinitions,
  });

  const { push } = useRouter();

  const columns: GridColDef<ContractDefinition>[] = [
    {
      field: "title",
      headerName: intl.formatMessage(messages.titleHeader),
      flex: 1,

      renderCell: (cell) => {
        return (
          <CustomLink
            href={PATH_ADMIN.contract_definition.edit(cell.row.id)}
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
        columns={columns}
        columnBuffer={3}
        onEditClick={(contractsDefinition: ContractDefinition) => {
          if (contractsDefinition.id === undefined) {
            return;
          }
          push(PATH_ADMIN.contract_definition.edit(contractsDefinition.id));
        }}
        onUseAsTemplateClick={(contractDefinition) => {
          if (contractDefinition.id === undefined) {
            return;
          }
          push(
            `${PATH_ADMIN.contract_definition.create}?from=${contractDefinition?.id}`,
          );
        }}
        getEntityName={(contractsDefinition) => {
          return contractsDefinition.name;
        }}
        onRemoveClick={(contractDefinition: ContractDefinition) => {
          paginatedResource.methods.delete(contractDefinition.id);
        }}
      />
    </SimpleCard>
  );
}
