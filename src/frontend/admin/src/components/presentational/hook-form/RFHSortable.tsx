import * as React from "react";
import { PropsWithChildren, useEffect } from "react";
import { Controller, useFormContext } from "react-hook-form";
import Box from "@mui/material/Box";
import FormHelperText from "@mui/material/FormHelperText";
import FormLabel from "@mui/material/FormLabel";
import {
  DndList,
  DndListProps,
  Row,
} from "@/components/presentational/dnd/DndList";
import ControlledSelect, {
  ControlledSelectProps,
  useControlledSelect,
} from "@/components/presentational/inputs/select/ControlledSelect";

interface Props<T extends Row> extends DndListProps<T> {
  name: string;
  label?: string;
  options?: T[];
  initialSelectedOptions?: T[];

  onAdd?: (item: T) => void;

  enableSearch?: boolean;
  searchSelectProps?: ControlledSelectProps<T>;
}

export function RHFSortable<T extends Row>({
  name,
  enableSearch = false,
  label,
  ...props
}: PropsWithChildren<Props<T>>) {
  const { control, setValue } = useFormContext();
  const searchSelect = useControlledSelect<T>(props.rows);
  const labelledby = label ? `${name}-${label}` : "";

  useEffect(() => {
    searchSelect.setSelectedOptions(props.rows);
    setValue(name, props.rows);
  }, [props.rows]);

  const onSelectItem = (item: T): void => {
    if (item === null) {
      return;
    }
    searchSelect.onSelectItem(item);
    props.onAdd?.(item);
  };

  const onSorted = (items: T[]): void => {
    setValue(name, items);
    props.onSorted(items);
  };

  return (
    <>
      {label && (
        <Box sx={{ marginBottom: 1.5 }}>
          <FormLabel id={labelledby}>{label}</FormLabel>
        </Box>
      )}
      {enableSearch && props.searchSelectProps && (
        <ControlledSelect
          {...props.searchSelectProps}
          size="small"
          onSelectItem={onSelectItem}
          selectedOptions={searchSelect.selectedOptions}
          sx={{ mb: 2 }}
        />
      )}
      <Controller
        name={name}
        control={control}
        render={({ fieldState: { error } }) => (
          <>
            <DndList {...props} onSorted={onSorted} />
            {!!error && (
              <FormHelperText error={!!error}>
                {error ? error?.message : ""}
              </FormHelperText>
            )}
          </>
        )}
      />
    </>
  );
}
