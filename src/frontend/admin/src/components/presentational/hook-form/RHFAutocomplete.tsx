import { Controller, useFormContext } from "react-hook-form";
import Autocomplete, { AutocompleteProps } from "@mui/material/Autocomplete";
import TextField from "@mui/material/TextField";
import Box from "@mui/material/Box";
import InputAdornment from "@mui/material/InputAdornment";
import React, { ReactNode } from "react";
import Divider from "@mui/material/Divider";
import { Maybe } from "@/types/utils";
import {
  SearchFilterComponentProps,
  useSearchFilterContext,
} from "@/components/presentational/filters/SearchFilters";
import { InitializeInputFilters } from "@/components/presentational/filters/InitializeInputFilters";

export type RHFAutocompleteProps<
  T,
  Multiple extends boolean | undefined,
  DisableClearable extends boolean | undefined = false,
  FreeSolo extends boolean | undefined = false,
> = Omit<
  AutocompleteProps<T, Multiple, DisableClearable, FreeSolo>,
  "renderInput"
> &
  SearchFilterComponentProps & {
    name: string;
    label?: string;
    helperText?: React.ReactNode;
    leftIcons?: React.ReactNode;
    placeholder?: string;
  };

export default function RHFAutocomplete<
  T,
  Multiple extends boolean | undefined = false,
  DisableClearable extends boolean | undefined = false,
  FreeSolo extends boolean | undefined = false,
>({
  name,
  label,
  helperText,
  leftIcons,
  placeholder,
  isFilterContext,
  filterQueryName,
  findFilterValue,
  ...other
}: Omit<
  RHFAutocompleteProps<T, Multiple, DisableClearable, FreeSolo>,
  "renderInput"
>) {
  const searchFilterContext = useSearchFilterContext(isFilterContext);
  const { control, setValue } = useFormContext();

  const getLeftIcons = (originLeft: Maybe<ReactNode>): Maybe<ReactNode> => {
    if (leftIcons === undefined) {
      return originLeft;
    }

    return (
      <>
        <Box display="flex" alignItems="center">
          {leftIcons && (
            <InputAdornment position="start">
              {leftIcons}
              <Divider sx={{ height: 28, m: 0.5 }} orientation="vertical" />
            </InputAdornment>
          )}
        </Box>
        {originLeft}
      </>
    );
  };

  const afterChange = (newValue?: T | T[]) => {
    if (!searchFilterContext) {
      return;
    }

    const isArray = Array.isArray(newValue);
    if (newValue && isArray && newValue.length > 0) {
      const values = newValue.map((val) => {
        return (
          other.getOptionLabel?.(val) ??
          (typeof val === "string" ? newValue : "")
        );
      });
      searchFilterContext.addChip({
        name,
        label: label ?? "",
        filterUrlName: filterQueryName ?? name,
        value: values.join(","),
        onDelete: () => setValue(name, []),
      });
    } else if (newValue && !isArray) {
      searchFilterContext.addChip({
        name,
        label: label ?? "",
        value:
          other.getOptionLabel?.(newValue) ??
          (typeof newValue === "string" ? newValue : ""),
        onDelete: () => setValue(name, null),
      });
    } else {
      searchFilterContext.removeChip(name);
    }
  };

  const getObject = async (values: string[]) => {
    if (!findFilterValue) {
      return undefined;
    }

    const result = await findFilterValue(values);
    afterChange(result);
    return result;
  };

  return (
    <InitializeInputFilters
      name={name}
      isFilterContext={isFilterContext}
      filterQueryName={filterQueryName ?? name}
      findFilterValue={getObject}
    >
      <Controller
        name={name}
        control={control}
        render={({ field, fieldState: { error } }) => (
          <Autocomplete
            {...field}
            renderInput={(params) => (
              <TextField
                label={label}
                error={!!error}
                placeholder={placeholder}
                helperText={error ? error?.message : helperText}
                {...params}
                InputProps={{
                  ...params.InputProps,
                  startAdornment: getLeftIcons(
                    params.InputProps.startAdornment,
                  ),
                }}
              />
            )}
            {...other}
            onChange={(event, newValue, reason, details) => {
              other.onChange?.(event, newValue, reason, details);
              afterChange(newValue as T | T[]);
              setValue(name, newValue, {
                shouldValidate: true,
                shouldDirty: true,
                shouldTouch: true,
              });
            }}
          />
        )}
      />
    </InitializeInputFilters>
  );
}
