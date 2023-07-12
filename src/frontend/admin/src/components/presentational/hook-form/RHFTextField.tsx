import TextField, { TextFieldProps } from "@mui/material/TextField";
import { Controller, useFormContext } from "react-hook-form";
import InputAdornment from "@mui/material/InputAdornment";
import IconButton from "@mui/material/IconButton";
import VisibilityIcon from "@mui/icons-material/Visibility";
import VisibilityOffIcon from "@mui/icons-material/VisibilityOff";
import { useState } from "react";
import { Maybe } from "@/types/utils";

type Props = TextFieldProps & {
  name: string;
};

export function RHFTextField({ name, helperText, ...props }: Props) {
  const { control } = useFormContext();
  const [showPassword, setShowPassword] = useState(false);

  const getType = (): Maybe<string> => {
    if (props.type === "password" && showPassword) {
      return "text";
    }

    return props.type;
  };

  return (
    <Controller
      name={name}
      control={control}
      render={({ field, fieldState: { error } }) => (
        <TextField
          {...field}
          fullWidth
          value={
            typeof field.value === "number" && field.value === 0
              ? ""
              : field.value
          }
          error={!!error}
          helperText={error ? error?.message : helperText}
          InputProps={{
            endAdornment: props.type === "password" && (
              <InputAdornment position="end">
                <IconButton
                  onClick={() => setShowPassword(!showPassword)}
                  edge="end"
                >
                  {showPassword ? <VisibilityOffIcon /> : <VisibilityIcon />}
                </IconButton>
              </InputAdornment>
            ),
          }}
          {...props}
          type={getType()}
        />
      )}
    />
  );
}
