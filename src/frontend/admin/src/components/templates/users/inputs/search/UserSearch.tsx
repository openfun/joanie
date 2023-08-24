import * as React from "react";
import { useState } from "react";
import {
  RHFAutocompleteSearchProps,
  RHFSearch,
} from "@/components/presentational/hook-form/RHFSearch";
import { Maybe } from "@/types/utils";
import { User } from "@/services/api/models/User";
import { useUsers } from "@/hooks/useUsers/useUsers";

export function UserSearch(props: RHFAutocompleteSearchProps<User>) {
  const [query, setQuery] = useState("");
  const users = useUsers({ query });

  return (
    <RHFSearch
      {...props}
      items={users.items}
      loading={users.states.fetching}
      onFilter={(term) => setQuery(term)}
      getOptionLabel={(option: Maybe<User>) => option?.username ?? ""}
      isOptionEqualToValue={(option, value) =>
        option.username === value.username
      }
    />
  );
}
