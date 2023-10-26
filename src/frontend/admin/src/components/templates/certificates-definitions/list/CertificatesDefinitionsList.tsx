import * as React from "react";
import { defineMessages, useIntl } from "react-intl";
import { useRouter } from "next/router";
import { GridColDef } from "@mui/x-data-grid";
import { TableComponent } from "@/components/presentational/table/TableComponent";
import { PATH_ADMIN } from "@/utils/routes/path";
import { CertificateDefinition } from "@/services/api/models/CertificateDefinition";
import { useCertificateDefinitions } from "@/hooks/useCertificateDefinitions/useCertificateDefinitions";
import { CustomLink } from "@/components/presentational/link/CustomLink";
import { commonTranslations } from "@/translations/common/commonTranslations";
import { SimpleCard } from "@/components/presentational/card/SimpleCard";
import { usePaginatedTableResource } from "@/components/presentational/table/usePaginatedTableResource";

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
  const paginatedResource = usePaginatedTableResource<CertificateDefinition>({
    useResource: useCertificateDefinitions,
  });
  const { push } = useRouter();

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
    <SimpleCard>
      <TableComponent
        columns={columns}
        columnBuffer={3}
        onEditClick={(certificateDefinition: CertificateDefinition) => {
          if (certificateDefinition.id === undefined) {
            return;
          }
          push(PATH_ADMIN.certificates.edit(certificateDefinition.id));
        }}
        {...paginatedResource.tableProps}
        getEntityName={(certificateDefinition) => {
          return certificateDefinition.name;
        }}
        onRemoveClick={(certificateDefinition: CertificateDefinition) => {
          paginatedResource.methods.delete(certificateDefinition.id);
        }}
      />
    </SimpleCard>
  );
}
