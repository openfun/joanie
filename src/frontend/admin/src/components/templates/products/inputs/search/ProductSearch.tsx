import * as React from "react";
import { useState } from "react";
import {
  RHFAutocompleteSearchProps,
  RHFSearch,
} from "@/components/presentational/hook-form/RHFSearch";
import { Maybe } from "@/types/utils";
import { useProducts } from "@/hooks/useProducts/useProducts";
import { Product } from "@/services/api/models/Product";

export function ProductSearch(props: RHFAutocompleteSearchProps<Product>) {
  const [search, setSearch] = useState("");
  const courses = useProducts({ search }, { enabled: search !== "" });

  return (
    <RHFSearch
      {...props}
      items={courses.items}
      loading={courses.states.fetching}
      onFilter={(term) => setSearch(term)}
      getOptionLabel={(option: Maybe<Product>) => option?.title ?? ""}
      isOptionEqualToValue={(option, value) => option.title === value.title}
    />
  );
}
