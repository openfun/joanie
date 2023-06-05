import * as React from "react";
import { PropsWithChildren } from "react";
import { Controller, useFieldArray, useFormContext } from "react-hook-form";
import Box from "@mui/material/Box";
import FormHelperText from "@mui/material/FormHelperText";
import FormLabel from "@mui/material/FormLabel";
import {
  DndList,
  DndListProps,
  Row,
} from "@/components/presentational/dnd/DndList";

interface Props<T extends Row> extends DndListProps<T> {
  name: string;
  label?: string;
  initialSelectedOptions?: T[];
}

export function RHFSortable<T extends Row>({
  name,
  label,
  ...props
}: PropsWithChildren<Props<T>>) {
  const { control } = useFormContext();
  const { fields, replace: replaceArray } = useFieldArray({
    control, // control props comes from useForm (optional: if you are using FormContext)
    name, // unique name for your Field Array
  });
  const labelledby = label ? `${name}-${label}` : "";

  const onSorted = (items: T[]): void => {
    replaceArray(items);
  };

  return (
    <>
      {label && (
        <Box sx={{ marginBottom: 1.5 }}>
          <FormLabel id={labelledby}>{label}</FormLabel>
        </Box>
      )}
      <Controller
        name={name}
        control={control}
        render={({ fieldState: { error } }) => (
          <>
            <DndList
              {...props}
              droppableId={props.droppableId}
              rows={fields as T[]}
              onSorted={onSorted}
            />
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
