import * as React from "react";
import { useState } from "react";
import {
  RHFAutocompleteSearchProps,
  RHFSearch,
} from "@/components/presentational/hook-form/RHFSearch";
import { Maybe } from "@/types/utils";
import { User } from "@/services/api/models/User";
import { useUsers } from "@/hooks/useUsers/useUsers";
import { UserRepository } from "@/services/repositories/Users/UsersRepository";

export function UserSearch(props: RHFAutocompleteSearchProps<User>) {
  const [query, setQuery] = useState("");
  const users = useUsers({ query });

  return (
    <RHFSearch
      {...props}
      findFilterValue={async (values) => {
        const request = await UserRepository.getAll({ ids: values });
        return request.results;
      }}
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
