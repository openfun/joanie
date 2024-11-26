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
  props: Omit<ControlledSelectProps<Organization>, "options">,
) {
  const [query, setQuery] = useState("");
  const organizations = useOrganizations({ query });

  const debouncedSetQuery = useDebouncedCallback(setQuery, 300);

  return (
    <ControlledSelect
      {...props}
      options={organizations.items}
      loading={organizations.states.fetching}
      onFilter={debouncedSetQuery}
      label="Search organization"
      getOptionLabel={(option: Maybe<Organization>) => option?.title ?? ""}
      isOptionEqualToValue={(option, value) => option.code === value.code}
    />
  );
}
