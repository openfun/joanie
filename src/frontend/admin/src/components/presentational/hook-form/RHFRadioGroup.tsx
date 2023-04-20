import { Controller, useFormContext } from "react-hook-form";
import {
  FormControl,
  FormControlLabel,
  FormHelperText,
  FormLabel,
  Radio,
  RadioGroup,
  RadioGroupProps,
} from "@mui/material";

type Props = RadioGroupProps & {
  name: string;
  options: { label: string; value: any }[];
  label?: string;
  helperText?: React.ReactNode;
};

export default function RHFRadioGroup({
  row,
  name,
  label,
  options,
  helperText,
  ...other
}: Props) {
  const { control } = useFormContext();

  const labelledby = label ? `${name}-${label}` : "";

  return (
    <Controller
      name={name}
      control={control}
      render={({ field, fieldState: { error } }) => (
        <FormControl>
          {label && (
            <FormLabel component="legend" id={labelledby}>
              {label}
            </FormLabel>
          )}

          <RadioGroup
            {...field}
            aria-labelledby={labelledby}
            row={row}
            {...other}
          >
            {options.map((option) => (
              <FormControlLabel
                key={option.value}
                value={option.value}
                control={<Radio />}
                label={option.label}
              />
            ))}
          </RadioGroup>

          {(!!error || helperText) && (
            <FormHelperText error={!!error}>
              {error ? error?.message : helperText}
            </FormHelperText>
          )}
        </FormControl>
      )}
    />
  );
}
