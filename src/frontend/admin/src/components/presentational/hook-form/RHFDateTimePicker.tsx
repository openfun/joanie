import { Controller, useFormContext } from "react-hook-form";
import { DateTimePicker, DateTimePickerProps } from "@mui/x-date-pickers";
import FormHelperText from "@mui/material/FormHelperText";

type Props = DateTimePickerProps<any> & {
  name: string;
  label: string;
};

export function RHFDateTimePicker({ label, name, ...props }: Props) {
  const { control, getValues, setValue } = useFormContext();
  const value = getValues(name);
  return (
    <Controller
      name={name}
      control={control}
      render={({ field, fieldState: { error } }) => (
        <div>
          <DateTimePicker
            {...field}
            value={value ? new Date(value) : null}
            slotProps={{
              ...props.slotProps,
              desktopPaper: {
                // @ts-ignore
                "data-testid": "date-picker",
                ...props.slotProps?.desktopPaper,
              },
              mobilePaper: {
                // @ts-ignore
                "data-testid": "date-picker",
                ...props.slotProps?.mobilePaper,
              },
            }}
            onChange={(newValue: Date | null) => {
              if (newValue === null) {
                setValue(name, undefined);
              } else {
                setValue(name, newValue.toISOString());
              }
            }}
            sx={{ width: "100%" }}
            label={label}
          />
          {!!error && (
            <FormHelperText error={true}>{error.message}</FormHelperText>
          )}
        </div>
      )}
    />
  );
}
