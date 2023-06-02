import * as React from "react";
import { useState } from "react";
import Autocomplete, { AutocompleteProps } from "@mui/material/Autocomplete";
import TextField from "@mui/material/TextField";

export interface ControlledSelectProps<T>
  extends Omit<AutocompleteProps<T, false, false, false>, "renderInput"> {
  onSelectItem?: (item: T) => void;
  label?: string;
  selectedOptions?: T[];
  onFilter?: (term: string) => void;
}

export default function ControlledSelect<T>({
  label,
  onSelectItem,
  selectedOptions,
  onFilter,
  ...props
}: Omit<ControlledSelectProps<T>, "renderInput">) {
  const [inputValue, setInputValue] = useState("");

  return (
    <Autocomplete
      onChange={(event, newValue) => {
        onSelectItem?.(newValue as T);
      }}
      inputValue={inputValue}
      loading={props.loading}
      onInputChange={(event, newInputValue, reason) => {
        if (reason === "reset") {
          setInputValue("");
        } else {
          setInputValue(newInputValue);
          onFilter?.(newInputValue);
        }
      }}
      renderInput={(params) => <TextField {...params} label={label} />}
      {...props}
    />
  );
}

export const useControlledSelect = <T extends unknown>(
  initialSelectedOptions: T[] = []
) => {
  const [selectedOptions, setSelectedOptions] = useState<T[]>(
    initialSelectedOptions
  );

  const onSelectItem = (option: T) => {
    const newOptions = [...selectedOptions];
    newOptions.push(option);
    setSelectedOptions(newOptions);
  };

  return {
    onSelectItem,
    selectedOptions,
    setSelectedOptions,
  };
};
