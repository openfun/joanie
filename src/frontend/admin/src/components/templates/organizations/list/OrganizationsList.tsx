import * as React from "react";
import { useState } from "react";
import { GridColDef } from "@mui/x-data-grid";
import { defineMessages, useIntl } from "react-intl";
import { useRouter } from "next/router";
import { useDebouncedCallback } from "use-debounce";
import { Organization } from "@/services/api/models/Organization";
import { TableComponent } from "@/components/presentational/table/TableComponent";
import { PATH_ADMIN } from "@/utils/routes/path";
import { useOrganizations } from "@/hooks/useOrganizations/useOrganizations";
import { Maybe } from "@/types/utils";
import { CustomLink } from "@/components/presentational/link/CustomLink";
import { commonTranslations } from "@/translations/common/commonTranslations";
import { SimpleCard } from "@/components/presentational/card/SimpleCard";

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

export function OrganizationsList() {
  const intl = useIntl();
  const { push } = useRouter();
  const [query, setQuery] = useState<Maybe<string>>();
  const orgs = useOrganizations({ query });

  const debouncedSetQuery = useDebouncedCallback(setQuery, 300);

  const columns: GridColDef[] = [
    {
      field: "code",
      headerName: intl.formatMessage(messages.codeHeader),
      maxWidth: 200,
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
        rows={orgs.items}
        loading={orgs.states.isLoading || orgs.states.fetching}
        columns={columns}
        columnBuffer={3}
        onSearch={debouncedSetQuery}
        onEditClick={(organization: Organization) =>
          push(PATH_ADMIN.organizations.edit(organization.id))
        }
        onRemoveClick={(organization: Organization) => {
          orgs.methods.delete(organization.id);
        }}
        getEntityName={(organization) => {
          return organization.title;
        }}
      />
    </SimpleCard>
  );
}
