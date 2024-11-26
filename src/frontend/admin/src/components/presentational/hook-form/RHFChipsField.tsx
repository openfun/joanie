import * as React from "react";
import { Controller, useFormContext } from "react-hook-form";
import Autocomplete, { AutocompleteProps } from "@mui/material/Autocomplete";
import { ChipTypeMap } from "@mui/material/Chip";
import CircularProgress from "@mui/material/CircularProgress";
import IconButton from "@mui/material/IconButton";
import AddIcon from "@mui/icons-material/Add";
import Divider from "@mui/material/Divider";
import TextField from "@mui/material/TextField";
import { ButtonProps } from "@mui/material/Button";
import { defineMessages, useIntl } from "react-intl";

const messages = defineMessages({
  createResource: {
    id: "components.presentational.hookForm.RHFChipsField.createResource",
    description: "Button label to create a resource",
    defaultMessage: "Create a resource",
  },
});

type ChipsFieldsProps<
  Value,
  ChipComponent extends React.ElementType = ChipTypeMap["defaultComponent"],
> = Omit<
  AutocompleteProps<Value, true, boolean | undefined, false, ChipComponent>,
  "multiple" | "freeSolo"
>;

type RHFChipsFieldProps<
  Value,
  ChipComponent extends React.ElementType = ChipTypeMap["defaultComponent"],
> = Omit<
  ChipsFieldsProps<Value, ChipComponent>,
  "renderInput" | "filterOptions" | "value"
> & {
  helperText?: string;
  label: string;
  name: string;
  onCreateTag?: () => void;
  renderTagEditForm?: (field: any) => React.ReactNode;
};

function RHFChipsField<
  Value,
  ChipComponent extends React.ElementType = ChipTypeMap["defaultComponent"],
>({
  helperText,
  label,
  name,
  onCreateTag,
  renderTagEditForm,
  ...props
}: RHFChipsFieldProps<Value, ChipComponent>) {
  const { control } = useFormContext();
  const intl = useIntl();

  return (
    <Controller
      name={name}
      control={control}
      render={({ field }) => (
        <>
          <ChipsField
            {...props}
            value={field.value}
            filterOptions={(options) => options}
            onBlur={(event) => {
              props.onBlur?.(event);
              field.onBlur();
            }}
            onChange={(event, value, reason, details) => {
              field.onChange(value);
              props.onChange?.(event, value, reason, details);
            }}
            renderInput={(params) => (
              <TextField
                {...params}
                label={label}
                helperText={helperText}
                slotProps={{
                  input: {
                    ...params.InputProps,
                    startAdornment: (
                      <>
                        <CreateAdornment
                          onClick={onCreateTag}
                          title={intl.formatMessage(messages.createResource)}
                        />
                        {params.InputProps.startAdornment}
                      </>
                    ),
                    endAdornment: (
                      <>
                        <LoadingAdornment loading={props.loading} />
                        {params.InputProps.endAdornment}
                      </>
                    ),
                  },
                }}
              />
            )}
          />
          {renderTagEditForm?.(field)}
        </>
      )}
    />
  );
}

function ChipsField<
  Value,
  ChipComponent extends React.ElementType = ChipTypeMap["defaultComponent"],
>(props: ChipsFieldsProps<Value, ChipComponent>) {
  return <Autocomplete {...props} multiple />;
}

function CreateAdornment({ onClick, ...props }: ButtonProps) {
  if (!onClick) return null;

  return (
    <>
      <IconButton onClick={onClick} size="small" {...props}>
        <AddIcon color="primary" />
      </IconButton>
      <Divider sx={{ height: 28, m: 0.5 }} orientation="vertical" />
    </>
  );
}

type LoadingAdornmentProps = {
  loading?: boolean;
};
function LoadingAdornment({ loading }: LoadingAdornmentProps) {
  if (!loading) return null;

  return <CircularProgress color="inherit" size={20} />;
}

export default RHFChipsField;
