import TextField, { TextFieldProps } from "@mui/material/TextField";
import { Controller, useFormContext } from "react-hook-form";

type Props = TextFieldProps & {
  name: string;
};

export function RHFTextField({ name, helperText, ...props }: Props) {
  const { control } = useFormContext();

  return (
    <Controller
      name={name}
      control={control}
      render={({ field, fieldState: { error } }) => (
        <TextField
          {...field}
          fullWidth
          value={field.value}
          error={!!error}
          helperText={error ? error?.message : helperText}
          {...props}
        />
      )}
    />
  );
}
