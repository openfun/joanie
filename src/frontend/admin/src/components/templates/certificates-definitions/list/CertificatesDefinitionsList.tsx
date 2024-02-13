import * as React from "react";
import { defineMessages, useIntl } from "react-intl";
import { useRouter } from "next/router";
import { GridColDef } from "@mui/x-data-grid";
import {
  DefaultTableProps,
  TableComponent,
} from "@/components/presentational/table/TableComponent";
import { PATH_ADMIN } from "@/utils/routes/path";
import { CertificateDefinition } from "@/services/api/models/CertificateDefinition";
import {
  CertificateDefinitionResourceQuery,
  useCertificateDefinitions,
} from "@/hooks/useCertificateDefinitions/useCertificateDefinitions";
import { CustomLink } from "@/components/presentational/link/CustomLink";
import { commonTranslations } from "@/translations/common/commonTranslations";
import { SimpleCard } from "@/components/presentational/card/SimpleCard";
import { usePaginatedTableResource } from "@/components/presentational/table/usePaginatedTableResource";
import { CertificateDefinitionFilters } from "@/components/templates/certificates-definitions/filters/CertificateDefinitionFilters";

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

type Props = DefaultTableProps<CertificateDefinition>;

export function CertificatesDefinitionsList(props: Props) {
  const intl = useIntl();
  const { push } = useRouter();

  const paginatedResource = usePaginatedTableResource<
    CertificateDefinition,
    CertificateDefinitionResourceQuery
  >({
    useResource: useCertificateDefinitions,
    changeUrlOnPageChange: props.changeUrlOnPageChange,
  });

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
        {...paginatedResource.tableProps}
        {...props}
        filters={
          <CertificateDefinitionFilters {...paginatedResource.filtersProps} />
        }
        columns={columns}
        columnBuffer={3}
        onEditClick={(certificateDefinition: CertificateDefinition) => {
          if (certificateDefinition.id === undefined) {
            return;
          }
          push(PATH_ADMIN.certificates.edit(certificateDefinition.id));
        }}
        onUseAsTemplateClick={(certificateDefinition) => {
          if (certificateDefinition.id === undefined) {
            return;
          }
          push(
            `${PATH_ADMIN.certificates.create}?from=${certificateDefinition?.id}`,
          );
        }}
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
