import { Controller, useFormContext } from "react-hook-form";
import TextField, { TextFieldProps } from "@mui/material/TextField";
import * as React from "react";
import { ReactNode, useMemo } from "react";
import MenuItem from "@mui/material/MenuItem";
import Box from "@mui/material/Box";
import InputAdornment from "@mui/material/InputAdornment";
import Divider from "@mui/material/Divider";
import { FormattedMessage } from "react-intl";
import ClearIcon from "@mui/icons-material/Clear";
import IconButton from "@mui/material/IconButton";
import { Maybe } from "@/types/utils";
import { commonTranslations } from "@/translations/common/commonTranslations";
import {
  SearchFilterComponentProps,
  useSearchFilterContext,
} from "@/components/presentational/filters/SearchFilters";
import { InitializeInputFilters } from "@/components/presentational/filters/InitializeInputFilters";

export interface SelectOption<OptionValue = any> {
  label: string;
  value: OptionValue;
}

export type RHFSelectProps = Omit<TextFieldProps, "label"> &
  SearchFilterComponentProps & {
    name: string;
    label?: string;
    getOptionLabel?: (value: any) => string;
    native?: boolean;
    noneOption?: boolean;
    maxHeight?: boolean | number;
    children?: React.ReactNode;
    options?: SelectOption[];
    leftIcons?: ReactNode;
    afterChange?: (newValue: any | null) => void;
  };

export function RHFSelect({
  name,
  helperText,
  children,
  options = [],
  noneOption = false,
  leftIcons,
  getOptionLabel,
  isFilterContext,
  findFilterValue,
  filterQueryName,
  afterChange,
  ...other
}: RHFSelectProps) {
  const searchFilterContext = useSearchFilterContext(isFilterContext);
  const { control, setValue } = useFormContext();
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

  const addOrRemoveChip = (newValue?: string) => {
    if (!isFilterContext) {
      return;
    }

    if (afterChange) {
      afterChange(newValue);
    } else if (newValue) {
      searchFilterContext?.addChip({
        name,
        label: other.label ?? "",
        value: getOptionLabel ? getOptionLabel(newValue) : newValue,
        onDelete: (chipName: string) => setValue(chipName, ""),
      });
    } else {
      searchFilterContext?.removeChip(name);
    }
  };

  const clickOnDelete = () => {
    afterChange?.("");
    addOrRemoveChip(undefined);
  };

  return (
    <InitializeInputFilters
      name={name}
      isFilterContext={isFilterContext}
      filterQueryName={filterQueryName ?? name}
      findFilterValue={async (values) => {
        const value = values[0];
        addOrRemoveChip(value);
        return value;
      }}
    >
      <Controller
        name={name}
        control={control}
        render={({ field, fieldState: { error } }) => (
          <TextField
            {...field}
            onChange={(e) => {
              field.onChange(e);
              setValue(name, e.target.value, { shouldTouch: true });
              addOrRemoveChip?.(e.target.value);
            }}
            sx={{
              "&:hover": {
                ".clear-select-button": {
                  opacity: 1,
                },
              },
            }}
            select
            InputProps={{
              startAdornment: leftIconsElement,
              endAdornment: (
                <IconButton
                  size="small"
                  className="clear-select-button"
                  sx={{
                    mr: 2,
                    opacity: 0,
                  }}
                  onClick={() => {
                    field.onChange({ target: { value: "" } });
                    clickOnDelete();
                  }}
                >
                  <ClearIcon fontSize="small" />
                </IconButton>
              ),
              inputProps: {
                "data-testid": "select-value",
              },
            }}
            fullWidth
            error={!!error}
            helperText={error ? error?.message : helperText}
            {...other}
          >
            {noneOption && (
              <MenuItem value="">
                <em>
                  <FormattedMessage {...commonTranslations.none} />
                </em>
              </MenuItem>
            )}
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
    </InitializeInputFilters>
  );
}
