import * as React from "react";
import { GridColDef } from "@mui/x-data-grid";
import { defineMessages, useIntl } from "react-intl";
import { useRouter } from "next/router";
import { Organization } from "@/services/api/models/Organization";
import {
  DefaultTableProps,
  TableComponent,
} from "@/components/presentational/table/TableComponent";
import { PATH_ADMIN } from "@/utils/routes/path";
import { useOrganizations } from "@/hooks/useOrganizations/useOrganizations";
import { CustomLink } from "@/components/presentational/link/CustomLink";
import { commonTranslations } from "@/translations/common/commonTranslations";
import { SimpleCard } from "@/components/presentational/card/SimpleCard";
import { usePaginatedTableResource } from "@/components/presentational/table/usePaginatedTableResource";
import { OrganizationFilters } from "@/components/templates/organizations/filters/OrganizationFilters";

const messages = defineMessages({
  codeHeader: {
    id: "components.templates.organizations.list.codeHeader",
    defaultMessage: "Code",
    description: "Label for the code header inside the table  ",
  },
  title: {
    id: "components.templates.organizations.list.title",
    defaultMessage: "Title",
    description: "Label for the title header inside the table  ",
  },
});

type Props = DefaultTableProps<Organization>;

export function OrganizationsList(props: Props) {
  const intl = useIntl();
  const { push } = useRouter();
  const paginatedResource = usePaginatedTableResource<Organization>({
    useResource: useOrganizations,
    changeUrlOnPageChange: props.changeUrlOnPageChange,
  });

  const columns: GridColDef<Organization>[] = [
    {
      field: "code",
      headerName: intl.formatMessage(messages.codeHeader),
      maxWidth: 200,
      renderCell: (cell) => {
        return (
          <CustomLink
            href={PATH_ADMIN.organizations.edit(cell.row.id)}
            title={intl.formatMessage(commonTranslations.edit)}
          >
            {cell.row.code}
          </CustomLink>
        );
      },
    },
    {
      field: "title",
      headerName: intl.formatMessage(messages.title),
      flex: 1,
      renderCell: (cell) => {
        return (
          <CustomLink
            href={PATH_ADMIN.organizations.edit(cell.row.id)}
            title={intl.formatMessage(commonTranslations.edit)}
          >
            {cell.row.title}
          </CustomLink>
        );
      },
    },
  ];

  return (
    <SimpleCard>
      <TableComponent
        {...paginatedResource.tableProps}
        {...props}
        filters={
          <OrganizationFilters
            onSearch={paginatedResource.tableProps.onSearch}
            loading={paginatedResource.tableProps.loading}
          />
        }
        columns={columns}
        columnBuffer={3}
        onEditClick={(organization: Organization) =>
          push(PATH_ADMIN.organizations.edit(organization.id))
        }
        onRemoveClick={(organization: Organization) => {
          paginatedResource.methods.delete(organization.id);
        }}
        onUseAsTemplateClick={(organization) => {
          if (organization.id === undefined) {
            return;
          }
          push(`${PATH_ADMIN.organizations.create}?from=${organization?.id}`);
        }}
        getEntityName={(organization) => {
          return organization.title;
        }}
      />
    </SimpleCard>
  );
}
