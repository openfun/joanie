import * as React from "react";
import { useMemo } from "react";
import { GridColDef } from "@mui/x-data-grid";
import { defineMessages, useIntl } from "react-intl";
import { TableComponent } from "../../../presentational/table/TableComponent";
import { Accesses, DTOAccesses } from "@/services/api/models/Accesses";
import { SelectAccess } from "@/components/templates/accesses/list/SelectAccess";
import { AddUserAccess } from "@/components/templates/accesses/list/AddUserAccess";
import { SelectOption } from "@/components/presentational/hook-form/RHFSelect";
import { User } from "@/services/api/models/User";

const messages = defineMessages({
  fullnameHeader: {
    id: "components.template.accesses.list.AccessesList.fullnameHeader",
    defaultMessage: "Fullname",
    description: "Fullname column header label",
  },
  usernameHeader: {
    id: "components.template.accesses.list.AccessesList.usernameHeader",
    defaultMessage: "Username",
    description: "Username column header label",
  },
  roleHeader: {
    id: "components.template.accesses.list.AccessesList.roleHeader",
    defaultMessage: "User role",
    description: "Role column header label",
  },
});

type Props = {
  accesses: Accesses[];
  availableAccesses: SelectOption[];
  defaultRole?: string;
  onAdd: (user: User, role: string) => void;
  onRemove: (accessId: string) => Promise<void>;
  onUpdateAccess: (accessId: string, payload: DTOAccesses) => Promise<void>;
};

export function AccessesList(props: Props) {
  const intl = useIntl();
  const columns: GridColDef<Accesses>[] = useMemo(() => {
    return [
      {
        field: "user.username",
        headerName: intl.formatMessage(messages.usernameHeader),
        valueGetter: (params) => {
          return params.row.user.username;
        },
        flex: 1,
      },
      {
        flex: 1,
        field: "role",
        headerName: intl.formatMessage(messages.roleHeader),
        renderCell: (params) => (
          <SelectAccess
            onUpdateAccess={props.onUpdateAccess}
            availableAccesses={props.availableAccesses}
            access={params.row}
          />
        ),
      },
    ];
  }, []);

  return (
    <TableComponent
      paginationMode="client"
      rows={props.accesses}
      columns={columns}
      onRemoveClick={(row) => {
        props.onRemove(row.id);
      }}
      topActions={
        <AddUserAccess
          onAdd={props.onAdd}
          allAccesses={props.availableAccesses}
          defaultRole={props.defaultRole ?? props.availableAccesses[0].value}
        />
      }
    />
  );
}
