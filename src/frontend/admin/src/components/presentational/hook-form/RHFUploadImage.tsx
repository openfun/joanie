import * as React from "react";
import { useRef, useState } from "react";
import { Controller, useFormContext } from "react-hook-form";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Collapse from "@mui/material/Collapse";
import { TransitionGroup } from "react-transition-group";
import UploadFileIcon from "@mui/icons-material/UploadFile";
import { useIntl } from "react-intl";
import Typography from "@mui/material/Typography";
import { FileThumbnail } from "@/components/presentational/files/thumbnail/FileThumbnail";
import { ThumbnailDetailField } from "@/services/api/models/Image";
import { commonTranslations } from "@/translations/common/commonTranslations";

interface Props {
  accept: string;
  name: string;
  label: string;
  buttonLabel?: string;
  thumbnailFiles?: ThumbnailDetailField[];
}

export function RHFUploadImage({
  name,
  accept,
  label,
  buttonLabel,
  thumbnailFiles = [],
}: Props) {
  const intl = useIntl();
  const { control, setValue } = useFormContext();
  const ref = useRef<HTMLInputElement>(null);

  const [files, setFiles] = useState<File[]>([]);
  const [replaceThumbnailIndex, setReplaceThumbnailIndex] = useState<number>();
  const [thumbnails, setThumbnails] =
    useState<ThumbnailDetailField[]>(thumbnailFiles);

  const onReplaceThumbnail = (index: number) => {
    setReplaceThumbnailIndex(index);
    ref.current?.click();
  };

  const onSelectFiles = (newFiles: File[]) => {
    // I want to test null and undefined
    if (replaceThumbnailIndex != null && replaceThumbnailIndex >= 0) {
      const allThumbnail = [...thumbnailFiles];
      allThumbnail?.splice(replaceThumbnailIndex, 1);
      setThumbnails(allThumbnail);
    }
    setFiles(newFiles);
    setValue(name, newFiles);
  };

  const hideUploadButton = thumbnailFiles?.length > 0 || files.length > 0;

  return (
    <div>
      <Controller
        name={name}
        control={control}
        render={({ field }) => {
          return (
            <>
              {label && <Typography variant="caption">{label}</Typography>}

              <Button
                variant="outlined"
                color="secondary"
                sx={{ ...(hideUploadButton ? { display: "none" } : {}) }}
                size="small"
                startIcon={<UploadFileIcon />}
                component="label"
              >
                {buttonLabel ?? intl.formatMessage(commonTranslations.upload)}
                <input
                  {...field}
                  ref={ref}
                  value=""
                  hidden
                  onChange={(event) => {
                    const allFiles = Array.from(event.target.files ?? []);
                    onSelectFiles(allFiles);
                    return field.onChange(allFiles);
                  }}
                  accept={accept}
                  multiple={false}
                  type="file"
                />
              </Button>
            </>
          );
        }}
      />
      <Box mt={1}>
        <TransitionGroup>
          {files?.map((item) => (
            <Collapse key={item.name}>
              <FileThumbnail
                file={item}
                onReplace={() => ref.current?.click()}
              />
            </Collapse>
          ))}
          {thumbnails?.map((item, index) => (
            <Collapse key={item.filename}>
              <FileThumbnail
                file={item}
                onReplace={() => onReplaceThumbnail(index)}
              />
            </Collapse>
          ))}
        </TransitionGroup>
      </Box>
    </div>
  );
}
