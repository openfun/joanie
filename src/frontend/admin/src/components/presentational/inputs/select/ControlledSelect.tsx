import * as React from "react";
import { ReactNode, useState } from "react";
import Autocomplete, { AutocompleteProps } from "@mui/material/Autocomplete";
import TextField from "@mui/material/TextField";
import Box from "@mui/material/Box";
import InputAdornment from "@mui/material/InputAdornment";
import Divider from "@mui/material/Divider";
import IconButton from "@mui/material/IconButton";
import AddIcon from "@mui/icons-material/Add";
import { ResourceWithId } from "@/services/api/models/Ressource";
import { Maybe } from "@/types/utils";

export interface ControlledSelectProps<T extends ResourceWithId>
  extends Omit<AutocompleteProps<T, false, false, false>, "renderInput"> {
  onSelectItem?: (item: T) => void;
  label?: string;
  selectedOptions?: T[];
  onFilter?: (term: string) => void;
  enableCreate?: boolean;
  onCreateClick?: () => void;
  leftIcons?: ReactNode;
}

export default function ControlledSelect<T extends ResourceWithId>({
  label,
  onSelectItem,
  selectedOptions,
  enableCreate = false,
  onCreateClick,
  leftIcons,
  onFilter,
  ...props
}: Omit<ControlledSelectProps<T>, "renderInput">) {
  const [inputValue, setInputValue] = useState("");

  const getLeftIcons = (): Maybe<ReactNode> => {
    if (!leftIcons && !enableCreate) {
      return undefined;
    }

    return (
      <Box display="flex" alignItems="center">
        <InputAdornment position="start">
          {leftIcons && (
            <>
              {leftIcons}
              <Divider sx={{ height: 28, m: 0.5 }} orientation="vertical" />
            </>
          )}
          {enableCreate && (
            <>
              <IconButton onClick={onCreateClick} size="small">
                <AddIcon color="primary" />
              </IconButton>
              <Divider sx={{ height: 28, m: 0.5 }} orientation="vertical" />
            </>
          )}
        </InputAdornment>
      </Box>
    );
  };

  return (
    <Autocomplete
      onChange={(event, newValue) => {
        if (newValue !== null) {
          onSelectItem?.(newValue as T);
        }
      }}
      inputValue={inputValue}
      getOptionDisabled={(option) => {
        if (!selectedOptions) {
          return false;
        }

        const index = selectedOptions.findIndex(
          (entity) => entity.id === option.id,
        );

        return index >= 0;
      }}
      loading={props.loading}
      onInputChange={(event, newInputValue, reason) => {
        if (reason === "reset") {
          setInputValue("");
        } else {
          setInputValue(newInputValue);
          onFilter?.(newInputValue);
        }
      }}
      renderInput={(params) => (
        <TextField
          {...params}
          InputProps={{
            ...params.InputProps,
            startAdornment: getLeftIcons(),
          }}
          label={label}
        />
      )}
      {...props}
    />
  );
}

export const useControlledSelect = <T extends unknown>(
  initialSelectedOptions: T[] = [],
) => {
  const [selectedOptions, setSelectedOptions] = useState<T[]>(
    initialSelectedOptions,
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
