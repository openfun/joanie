import { Controller, useFormContext } from "react-hook-form";
import { Autocomplete, AutocompleteProps, TextField } from "@mui/material";

export interface RHFAutocompleteProps<
  T,
  Multiple extends boolean | undefined,
  DisableClearable extends boolean | undefined = false,
  FreeSolo extends boolean | undefined = false
> extends Omit<
    AutocompleteProps<T, Multiple, DisableClearable, FreeSolo>,
    "renderInput"
  > {
  name: string;
  label?: string;
  helperText?: React.ReactNode;
}

export default function RHFAutocomplete<
  T,
  Multiple extends boolean | undefined = false,
  DisableClearable extends boolean | undefined = false,
  FreeSolo extends boolean | undefined = false
>({
  name,
  label,
  helperText,
  ...other
}: Omit<
  RHFAutocompleteProps<T, Multiple, DisableClearable, FreeSolo>,
  "renderInput"
>) {
  const { control, setValue } = useFormContext();

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
              helperText={error ? error?.message : helperText}
              {...params}
            />
          )}
          {...other}
          onChange={(event, newValue, reason, details) => {
            other.onChange?.(event, newValue, reason, details);
            setValue(name, newValue, { shouldValidate: true });
          }}
        />
      )}
    />
  );
}
