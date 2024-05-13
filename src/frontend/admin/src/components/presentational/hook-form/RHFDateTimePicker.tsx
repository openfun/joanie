import { Controller, useFormContext } from "react-hook-form";
import { DateTimePicker, DateTimePickerProps } from "@mui/x-date-pickers";
import FormHelperText from "@mui/material/FormHelperText";
import { defineMessages, useIntl } from "react-intl";

const messages = defineMessages({
  invalidDate: {
    id: "components.presentational.hookForm.RHFDateTimePicker.invalidDate",
    defaultMessage: "Invalid date",
    description: "Message displayed when a date entered is not a date",
  },
});

type Props = DateTimePickerProps<any> & {
  name: string;
  label: string;
};

export function RHFDateTimePicker({ label, name, ...props }: Props) {
  const intl = useIntl();
  const { control, getValues, setValue, setError } = useFormContext();
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
                const isValid = !Number.isNaN(newValue.getTime());
                if (isValid) {
                  setValue(name, newValue.toISOString());
                } else {
                  setError(name, {
                    type: "custom",
                    message: intl.formatMessage(messages.invalidDate),
                  });
                }
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
