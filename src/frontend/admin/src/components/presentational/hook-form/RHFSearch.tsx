import * as React from "react";
import { ReactNode, useEffect, useState } from "react";
import { useDebouncedCallback } from "use-debounce";
import { useFormContext } from "react-hook-form";
import IconButton from "@mui/material/IconButton";
import AddIcon from "@mui/icons-material/Add";
import ModeEditOutlineTwoToneIcon from "@mui/icons-material/ModeEditOutlineTwoTone";
import Divider from "@mui/material/Divider";
import RHFAutocomplete, {
  RHFAutocompleteProps,
} from "@/components/presentational/hook-form/RHFAutocomplete";
import { Maybe, Nullable } from "@/types/utils";
import { SearchFilterComponentProps } from "@/components/presentational/filters/SearchFilters";

export type RHFAutocompleteSearchProps<T> = Omit<
  RHFAutocompleteProps<T, Maybe<boolean>>,
  "options"
> & {
  enableAdd?: boolean;
  enableEdit?: boolean;
  onAddClick?: () => void;
  onEditClick?: () => void;
};

export interface RHFSearchProps<T> extends RHFAutocompleteSearchProps<T> {
  items: T[];
  onFilter: (searchTerm: string) => void;
}

export function RHFSearch<T>({
  enableAdd,
  enableEdit,
  onAddClick,
  onEditClick,
  items,
  onFilter,
  ...props
}: RHFSearchProps<T> & SearchFilterComponentProps) {
  const { getValues } = useFormContext();
  const value: Nullable<T> = getValues(props.name);
  const [search, setSearch] = useState("");
  const [selectedOptions, setSelectedOptions] = useState<T | T[]>();
  const [options, setOptions] = useState<T[]>([]);

  const onChangeSearchInput = useDebouncedCallback(onFilter, 400);

  useEffect(() => {
    setSelectedOptions(getValues(props.name));
  }, [value]);

  useEffect(() => {
    const isArray = Array.isArray(selectedOptions);
    let result: T[] = [];
    if (isArray) {
      result = selectedOptions;
    } else if (selectedOptions !== null && selectedOptions !== undefined) {
      result = [selectedOptions];
    }

    setOptions([...items, ...result]);
  }, [items, search, selectedOptions]);

  const getLeftIcons = (): Maybe<ReactNode> => {
    const addEditButton = value && enableEdit;
    if (!addEditButton && !enableAdd) {
      return undefined;
    }
    return (
      <>
        {enableAdd && (
          <IconButton
            data-testid="search-add-button"
            onClick={onAddClick}
            size="small"
          >
            <AddIcon color="primary" />
          </IconButton>
        )}
        {enableAdd && addEditButton && (
          <Divider sx={{ height: 28, m: 0.5 }} orientation="vertical" />
        )}
        {addEditButton && (
          <IconButton
            onClick={onEditClick}
            size="small"
            data-testid="search-edit-button"
          >
            <ModeEditOutlineTwoToneIcon color="primary" />
          </IconButton>
        )}
      </>
    );
  };

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
        setSelectedOptions(newValue as T | T[]);
      }}
      includeInputInList
      leftIcons={getLeftIcons()}
      filterSelectedOptions={true}
      autoComplete
      options={options}
      filterOptions={(x) => x} // need to disable the built-in filtering of the Autocomplete component
    />
  );
}
