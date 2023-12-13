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
  const [query, setQuery] = useState("");
  const productQuery = useProducts({ query }, { enabled: query !== "" });

  return (
    <RHFSearch
      {...props}
      items={productQuery.items}
      loading={productQuery.states.fetching}
      onFilter={setQuery}
      getOptionLabel={(option: Maybe<Product>) => option?.title ?? ""}
      isOptionEqualToValue={(option, value) => option.title === value.title}
    />
  );
}
