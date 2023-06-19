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

  const onChangeSearchInput = useDebouncedCallback(onFilter, 400);

  useEffect(() => {
    setSelectedOptions(getValues(props.name));
  }, [getValues, props.name]);

  useEffect(() => {
    const isArray = Array.isArray(selectedOptions);
    let result: T[] = [];
    if (isArray) {
      result = selectedOptions;
    } else if (selectedOptions !== null && selectedOptions !== undefined) {
      result = [selectedOptions];
    }

    if (search === "") {
      setOptions(result);
    } else {
      setOptions([...items, ...result]);
    }
  }, [items, search, selectedOptions]);

  return (
    <RHFAutocomplete
      {...props}
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
