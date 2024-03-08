import { Controller, useFormContext } from "react-hook-form";
import FormControl from "@mui/material/FormControl";
import FormControlLabel from "@mui/material/FormControlLabel";
import FormHelperText from "@mui/material/FormHelperText";
import FormLabel from "@mui/material/FormLabel";
import Radio from "@mui/material/Radio";
import RadioGroup, { RadioGroupProps } from "@mui/material/RadioGroup";
import { SelectOption } from "@/components/presentational/hook-form/RHFSelect";
import {
  SearchFilterComponentProps,
  useSearchFilterContext,
} from "@/components/presentational/filters/SearchFilters";

type Props = RadioGroupProps &
  SearchFilterComponentProps & {
    name: string;
    options: SelectOption[];
    label?: string;
    helperText?: React.ReactNode;
    getValueLabel?: (value: string) => string;
  };

export default function RHFRadioGroup({
  row,
  name,
  label,
  options,
  helperText,
  isFilterContext,
  getValueLabel,
  ...other
}: Props) {
  const { control, setValue } = useFormContext();
  const searchFilterContext = useSearchFilterContext(isFilterContext);

  const labelledby = label ? `${name}-${label}` : "";

  const afterChange = (newValue?: string) => {
    if (!searchFilterContext) {
      return;
    }
    if (newValue && newValue !== "none" && newValue !== "") {
      const hasNoneOption =
        options.filter((option) => option.value === "none").length > 0;
      searchFilterContext.addChip({
        name,
        label: label ?? "",
        value: getValueLabel?.(newValue) ?? newValue,
        onDelete: () =>
          setValue(name, hasNoneOption ? "none" : "", {
            shouldValidate: true,
            shouldDirty: true,
          }),
      });
    } else {
      searchFilterContext.removeChip(name);
    }
  };

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
            onChange={(e, v) => {
              field.onChange(e, v);
              afterChange(v);
            }}
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
