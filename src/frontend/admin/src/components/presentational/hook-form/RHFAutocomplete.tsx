import { Controller, useFormContext } from "react-hook-form";
import Autocomplete, { AutocompleteProps } from "@mui/material/Autocomplete";
import TextField from "@mui/material/TextField";
import Box from "@mui/material/Box";
import InputAdornment from "@mui/material/InputAdornment";
import React, { ReactNode } from "react";
import Divider from "@mui/material/Divider";
import { Maybe } from "@/types/utils";

export interface RHFAutocompleteProps<
  T,
  Multiple extends boolean | undefined,
  DisableClearable extends boolean | undefined = false,
  FreeSolo extends boolean | undefined = false,
> extends Omit<
    AutocompleteProps<T, Multiple, DisableClearable, FreeSolo>,
    "renderInput"
  > {
  name: string;
  label?: string;
  helperText?: React.ReactNode;
  leftIcons?: React.ReactNode;
  placeholder?: string;
}

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
  ...other
}: Omit<
  RHFAutocompleteProps<T, Multiple, DisableClearable, FreeSolo>,
  "renderInput"
>) {
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

  return (
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
                startAdornment: getLeftIcons(params.InputProps.startAdornment),
              }}
            />
          )}
          {...other}
          onChange={(event, newValue, reason, details) => {
            other.onChange?.(event, newValue, reason, details);
            setValue(name, newValue, {
              shouldValidate: true,
              shouldDirty: true,
            });
          }}
        />
      )}
    />
  );
}
