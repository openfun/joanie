import FormControl from "@mui/material/FormControl";
import InputLabel from "@mui/material/InputLabel";
import * as React from "react";
import { PropsWithChildren } from "react";
import MenuItem from "@mui/material/MenuItem";
import Select, { SelectProps } from "@mui/material/Select";
import { defineMessages, useIntl } from "react-intl";
import Box from "@mui/material/Box";
import CircularProgress from "@mui/material/CircularProgress";
import ClearIcon from "@mui/icons-material/Clear";
import IconButton from "@mui/material/IconButton";
import { SelectOption } from "@/components/presentational/hook-form/RHFSelect";

const messages = defineMessages({
  none: {
    id: "components.presentational.button.popover.ButtonPopover.none",
    defaultMessage: "None",
    description: "None value label for the BasicSelect",
  },
});

interface Props extends Omit<SelectProps, "onSelect"> {
  options?: SelectOption[];
  value: any;
  onSelect: (newValue: any) => void;
  onClear?: () => void;
  label: string;
  loading?: boolean;
  enableClear?: boolean;
  showNoneValue?: boolean;
}
export function BasicSelect({
  label,
  value,
  showNoneValue = false,
  enableClear = false,
  onClear,
  loading = false,
  options = [],
  ...props
}: PropsWithChildren<Props>) {
  const intl = useIntl();
  return (
    <FormControl fullWidth>
      <InputLabel id={label}>{label}</InputLabel>
      <Select
        endAdornment={
          (loading || enableClear) && (
            <Box
              mr={2}
              display="flex"
              justifyContent="center"
              alignItems="center"
            >
              <>
                {loading && <CircularProgress size={16} />}
                {!loading && value && enableClear && (
                  <IconButton onClick={onClear}>
                    <ClearIcon fontSize="small" />
                  </IconButton>
                )}
              </>
            </Box>
          )
        }
        disabled={props.disabled ?? loading}
        labelId={label}
        value={value}
        label={label}
        onChange={(event) => props.onSelect(event.target.value)}
        {...props}
        inputProps={{
          "data-testid": "basic-select-input",
          ...props.inputProps,
        }}
      >
        {showNoneValue && (
          <MenuItem value="">{intl.formatMessage(messages.none)}</MenuItem>
        )}

        {options.map((option) => (
          <MenuItem key={option.value} value={option.value}>
            {option.label}
          </MenuItem>
        ))}
        {props.children}
      </Select>
    </FormControl>
  );
}
