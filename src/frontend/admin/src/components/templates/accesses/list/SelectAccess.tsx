import * as React from "react";
import { useEffect, useState } from "react";
import Box from "@mui/material/Box";
import { Accesses, DTOAccesses } from "@/services/api/models/Accesses";
import { BasicSelect } from "@/components/presentational/inputs/select/BasicSelect";
import { SelectOption } from "@/components/presentational/hook-form/RHFSelect";

type Props = {
  access: Accesses;
  availableAccesses: SelectOption[];
  onUpdateAccess: (accessId: string, payload: DTOAccesses) => Promise<void>;
};
export function SelectAccess(props: Props) {
  const [oldAccess, setOldAccess] = useState(props.access.role);
  const [access, setAccess] = useState(props.access.role);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    setAccess(props.access.role);
    setOldAccess(props.access.role);
  }, [props.access.role]);

  const handleChange = (newValue: string) => {
    setAccess(newValue);
    setIsLoading(true);

    props
      .onUpdateAccess(props.access.id, { role: newValue })
      .then(() => {
        setIsLoading(false);
        setOldAccess(newValue);
      })
      .catch(() => {
        setAccess(oldAccess);
        setIsLoading(false);
      });
  };

  return (
    <Box padding={1} width="100%">
      <BasicSelect
        options={props.availableAccesses}
        value={access}
        onSelect={handleChange}
        size="small"
        loading={isLoading}
        inputProps={{
          "aria-label": "User role",
        }}
        data-testid={`change-user-role-select-${props.access.user.id}`}
        label=""
      />
    </Box>
  );
}
