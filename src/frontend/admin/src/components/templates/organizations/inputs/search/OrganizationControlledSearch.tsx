import * as React from "react";
import { useState } from "react";
import { useDebouncedCallback } from "use-debounce";
import { useOrganizations } from "@/hooks/useOrganizations/useOrganizations";
import { Organization } from "@/services/api/models/Organization";
import { Maybe } from "@/types/utils";
import ControlledSelect, {
  ControlledSelectProps,
} from "@/components/presentational/inputs/select/ControlledSelect";

export function OrganizationControlledSearch(
  props: Omit<ControlledSelectProps<Organization>, "options">
) {
  const [search, setSearch] = useState("");
  const organizations = useOrganizations(
    { search },
    { enabled: search !== "" }
  );

  const onFilter = useDebouncedCallback((term: string) => {
    setSearch(term);
  }, 400);

  return (
    <ControlledSelect
      {...props}
      options={search === "" ? [] : organizations.items}
      loading={organizations.states.fetching}
      onFilter={onFilter}
      label="Search organization"
      getOptionLabel={(option: Maybe<Organization>) => option?.title ?? ""}
      isOptionEqualToValue={(option, value) => option.code === value.code}
    />
  );
}
