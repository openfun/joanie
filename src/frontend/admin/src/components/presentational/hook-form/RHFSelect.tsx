import { Controller, useFormContext } from "react-hook-form";
import TextField, { TextFieldProps } from "@mui/material/TextField";
import * as React from "react";
import { ReactNode, useMemo } from "react";
import MenuItem from "@mui/material/MenuItem";
import Box from "@mui/material/Box";
import InputAdornment from "@mui/material/InputAdornment";
import Divider from "@mui/material/Divider";
import { Maybe } from "@/types/utils";

export interface SelectOption {
  label: string;
  value: any;
}

type RHFSelectProps = TextFieldProps & {
  name: string;
  native?: boolean;
  maxHeight?: boolean | number;
  children?: React.ReactNode;
  options?: SelectOption[];
  leftIcons?: ReactNode;
};

export function RHFSelect({
  name,
  helperText,
  children,
  options = [],
  leftIcons,
  ...other
}: RHFSelectProps) {
  const { control } = useFormContext();

  const leftIconsElement = useMemo((): Maybe<ReactNode> => {
    if (leftIcons === undefined) {
      return undefined;
    }

    return (
      <Box display="flex" alignItems="center">
        {leftIcons && (
          <InputAdornment position="start">
            {leftIcons}
            <Divider sx={{ height: 28, m: 0.5 }} orientation="vertical" />
          </InputAdornment>
        )}
      </Box>
    );
  }, [leftIcons]);

  return (
    <Controller
      name={name}
      control={control}
      render={({ field, fieldState: { error } }) => (
        <TextField
          {...field}
          select
          InputProps={{
            startAdornment: leftIconsElement,
            inputProps: {
              "data-testid": "select-value",
            },
          }}
          fullWidth
          error={!!error}
          helperText={error ? error?.message : helperText}
          {...other}
        >
          {options?.map((option) => {
            return (
              <MenuItem key={option.label} value={option.value}>
                {option.label}
              </MenuItem>
            );
          })}
        </TextField>
      )}
    />
  );
}

// ----------------------------------------------------------------------
