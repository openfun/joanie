import * as React from "react";
import { useEffect, useState } from "react";
import { useDebouncedCallback } from "use-debounce";
import { useFormContext } from "react-hook-form";
import RHFAutocomplete, {
  RHFAutocompleteProps,
} from "@/components/presentational/hook-form/RHFAutocomplete";
import { Maybe } from "@/types/utils";

export interface RHFAutocompleteSearchProps<T>
  extends Omit<RHFAutocompleteProps<T, Maybe<boolean>>, "options"> {}

export interface RHFSearchProps<T> extends RHFAutocompleteSearchProps<T> {
  items: T[];
  onFilter: (searchTerm: string) => void;
}

export function RHFSearch<T>({ items, onFilter, ...props }: RHFSearchProps<T>) {
  const { getValues } = useFormContext();

  const [search, setSearch] = useState("");
  const [selectedOptions, setSelectedOptions] = useState<T | T[]>();
  const [options, setOptions] = useState<T[]>([]);

  const onChangeSearchInput = useDebouncedCallback((term: string) => {
    onFilter(term);
  }, 400);

  useEffect(() => {
    setSelectedOptions(getValues(props.name));
  }, []);

  useEffect(() => {
    const isArray = Array.isArray(selectedOptions);

    const result = isArray
      ? selectedOptions
      : selectedOptions != null
      ? [selectedOptions]
      : [];

    if (search === "") {
      setOptions(result);
    } else {
      setOptions([...items, ...result]);
    }
  }, [items, search, selectedOptions]);

  return (
    <RHFAutocomplete
      {...props}
      filterOptions={(x) => x}
      onInputChange={(event, inputValue) => {
        setSearch(inputValue);
        onChangeSearchInput(inputValue);
      }}
      onChange={(event, newValue) => {
        if (!newValue) {
          return;
        }
        setSelectedOptions(newValue);
      }}
      includeInputInList
      filterSelectedOptions={true}
      autoComplete
      options={options}
    />
  );
}
