import * as React from "react";
import { useState } from "react";
import { Controller, useFormContext } from "react-hook-form";
import { Box, Button, Collapse, FormLabel, IconButton } from "@mui/material";
// eslint-disable-next-line import/no-extraneous-dependencies
import { TransitionGroup } from "react-transition-group";

import UploadFileIcon from "@mui/icons-material/UploadFile";
import DeleteIcon from "@mui/icons-material/Delete";
import RefreshIcon from "@mui/icons-material/Refresh";
import { FileThumbnail } from "@/components/presentational/files/thumbnail/FileThumbnail";

interface Props {
  accept: string;
  name: string;
  label: string;
  multiple?: boolean;
  buttonLabel?: string;
}

export function RHFUpload({
  name,
  accept,
  label,
  multiple = false,
  buttonLabel,
}: Props) {
  const { control, setValue, getValues } = useFormContext();

  const [files, setFiles] = useState<File[]>([]);

  const onDelete = (index: number): void => {
    const allFiles = [...files];
    allFiles?.splice(index, 1);
    setFiles(allFiles);
    setValue(name, allFiles);
  };

  return (
    <div>
      <Controller
        name={name}
        control={control}
        render={({ field }) => {
          return (
            <>
              {label && (
                <FormLabel sx={{ mb: 1 }} component="legend">
                  {label}
                </FormLabel>
              )}
              {files.length === 0 && (
                <Button
                  variant="outlined"
                  color="secondary"
                  size="small"
                  startIcon={<UploadFileIcon />}
                  component="label"
                >
                  {buttonLabel ?? "Upload"}
                  <input
                    {...field}
                    value=""
                    hidden
                    onChange={(event) => {
                      const allFiles = Array.from(event.target.files ?? []);
                      setFiles(allFiles);
                      return field.onChange(allFiles);
                    }}
                    accept={accept}
                    multiple={multiple}
                    type="file"
                  />
                </Button>
              )}
            </>
          );
        }}
      />
      <Box mt={1}>
        <TransitionGroup>
          {files &&
            files.map((item, index) => (
              <Collapse key={item.name}>
                <FileThumbnail file={item} onDelete={() => onDelete(index)} />
              </Collapse>
            ))}
        </TransitionGroup>
        {files.length > 0 && (
          <Box display="flex" justifyContent="flex-end">
            <IconButton>
              <RefreshIcon />
            </IconButton>
            <IconButton color="error">
              <DeleteIcon />
            </IconButton>
          </Box>
        )}
      </Box>
    </div>
  );
}
