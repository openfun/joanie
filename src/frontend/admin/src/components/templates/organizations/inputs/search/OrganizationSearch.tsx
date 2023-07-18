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
  props: RHFAutocompleteSearchProps<Organization>,
) {
  const [query, setQuery] = useState("");
  const organizations = useOrganizations({ query }, { enabled: query !== "" });

  return (
    <RHFSearch
      {...props}
      items={organizations.items}
      loading={organizations.states.fetching}
      onFilter={setQuery}
      getOptionLabel={(option: Maybe<Organization>) => option?.title ?? ""}
      isOptionEqualToValue={(option, value) => option.title === value.title}
    />
  );
}
