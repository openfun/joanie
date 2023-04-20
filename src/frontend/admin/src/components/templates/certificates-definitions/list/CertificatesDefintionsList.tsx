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
  const [search, setSearch] = useState<Maybe<string>>();
  const certificateDefinitions = useCertificateDefinitions({ search });

  const debouncedSetSearch = useDebouncedCallback(setSearch, 300);

  const columns: GridColDef[] = [
    {
      field: "name",
      headerName: intl.formatMessage(messages.nameHeader),
      minWidth: 400,
    },
    {
      field: "title",
      headerName: intl.formatMessage(messages.titleHeader),
      flex: 1,
    },
  ];

  return (
    <TableComponent
      rows={certificateDefinitions.items}
      loading={certificateDefinitions.states.fetching}
      columns={columns}
      onSearch={debouncedSetSearch}
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
