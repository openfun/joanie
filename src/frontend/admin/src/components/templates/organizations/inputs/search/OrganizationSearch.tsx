import * as React from "react";
import { useState } from "react";
import { useOrganizations } from "@/hooks/useOrganizations/useOrganizations";
import {
  RHFAutocompleteSearchProps,
  RHFSearch,
} from "@/components/presentational/hook-form/RHFSearch";
import { Organization } from "@/services/api/models/Organization";
import { Maybe } from "@/types/utils";

export function OrganizationSearch(
  props: RHFAutocompleteSearchProps<Organization>
) {
  const [search, setSearch] = useState("");
  const organizations = useOrganizations(
    { search },
    { enabled: search !== "" }
  );

  return (
    <RHFSearch
      {...props}
      items={organizations.items}
      loading={organizations.states.fetching}
      onFilter={setSearch}
      getOptionLabel={(option: Maybe<Organization>) => option?.title ?? ""}
      isOptionEqualToValue={(option, value) => option.title === value.title}
    />
  );
}
