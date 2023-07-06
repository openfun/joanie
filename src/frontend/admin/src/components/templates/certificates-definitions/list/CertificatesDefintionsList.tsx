import * as React from "react";
import { useState } from "react";
import { defineMessages, useIntl } from "react-intl";
import { useRouter } from "next/router";
import { GridColDef } from "@mui/x-data-grid";
import { useDebouncedCallback } from "use-debounce";
import { TableComponent } from "@/components/presentational/table/TableComponent";
import { PATH_ADMIN } from "@/utils/routes/path";
import { CertificateDefinition } from "@/services/api/models/CertificateDefinition";
import { useCertificateDefinitions } from "@/hooks/useCertificateDefinitions/useCertificateDefinitions";
import { Maybe } from "@/types/utils";
import { CustomLink } from "@/components/presentational/link/CustomLink";
import { commonTranslations } from "@/translations/common/commonTranslations";

const messages = defineMessages({
  nameHeader: {
    id: "components.templates.certificatesDefinitions.list.nameHeader",
    defaultMessage: "Name",
    description: "Label for the Name header inside the table  ",
  },
  titleHeader: {
    id: "components.templates.certificatesDefinitions.list.titleHeader",
    defaultMessage: "Title",
    description: "Label for the title header inside the table  ",
  },
});

export function CertificatesDefinitionsList() {
  const intl = useIntl();
  const { push } = useRouter();
  const [query, setQuery] = useState<Maybe<string>>();
  const certificateDefinitions = useCertificateDefinitions({ query });

  const debouncedSetQuery = useDebouncedCallback(setQuery, 300);

  const columns: GridColDef<CertificateDefinition>[] = [
    {
      field: "name",
      headerName: intl.formatMessage(messages.nameHeader),
      minWidth: 400,
      renderCell: (cell) => {
        return (
          <CustomLink
            href={PATH_ADMIN.certificates.edit(cell.row.id)}
            title={intl.formatMessage(commonTranslations.edit)}
          >
            {cell.row.name}
          </CustomLink>
        );
      },
    },
    {
      field: "title",
      headerName: intl.formatMessage(messages.titleHeader),
      flex: 1,
      renderCell: (cell) => {
        return (
          <CustomLink
            href={PATH_ADMIN.certificates.edit(cell.row.id)}
            title={intl.formatMessage(commonTranslations.edit)}
          >
            {cell.row.title}
          </CustomLink>
        );
      },
    },
  ];

  return (
    <TableComponent
      rows={certificateDefinitions.items}
      loading={certificateDefinitions.states.fetching}
      columns={columns}
      onSearch={debouncedSetQuery}
      columnBuffer={3}
      onEditClick={(certificateDefinition: CertificateDefinition) => {
        if (certificateDefinition.id === undefined) {
          return;
        }
        push(PATH_ADMIN.certificates.edit(certificateDefinition.id));
      }}
      getEntityName={(certificateDefinition) => {
        return certificateDefinition.name;
      }}
      onRemoveClick={(certificateDefinition: CertificateDefinition) => {
        certificateDefinitions.methods.delete(certificateDefinition.id);
      }}
    />
  );
}
