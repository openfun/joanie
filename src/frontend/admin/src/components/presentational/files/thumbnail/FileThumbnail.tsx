import * as React from "react";
import { ReactNode } from "react";
import Box from "@mui/material/Box";
import IconButton from "@mui/material/IconButton";
import Typography from "@mui/material/Typography";
import ChangeCircleOutlinedIcon from "@mui/icons-material/ChangeCircleOutlined";
import { ThumbnailDetailField } from "@/services/api/models/Image";

interface Props {
  file: File | ThumbnailDetailField;
  onReplace?: () => void;
}

const isThumbnail = (
  item: File | ThumbnailDetailField,
): item is ThumbnailDetailField => {
  return "filename" in item;
};

export function FileThumbnail({ file, ...props }: Props) {
  const isThumb = isThumbnail(file);
  // Convert the size of a file in Bytes to a readable unit
  const formatFileSize = (bytes: number, decimalPoint = 2): string => {
    if (bytes === 0) return "0 Bytes";
    const k = 1000;
    const units = ["Bytes", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB"];
    const exponent = Math.floor(Math.log(bytes) / Math.log(k));
    return (
      parseFloat((bytes / k ** exponent).toFixed(decimalPoint)) +
      " " +
      units[exponent]
    );
  };

  const name: string = isThumb ? file.filename : file.name;
  const getPreview = (): ReactNode => {
    // eslint-disable-next-line compat/compat
    const src = isThumb ? file.src : URL.createObjectURL(file);
    const width = 100;
    const height = 60;
    return (
      <Box width={width} height={height} sx={{ marginLeft: 1 }}>
        <img
          alt="file-preview"
          style={{
            objectFit: "contain",
            objectPosition: "auto auto",
          }}
          width={width}
          height={height}
          src={src}
          srcSet={isThumb ? file.srcset : undefined}
        />
      </Box>
    );
  };

  return (
    <Box
      key={name}
      sx={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        p: 1.25,
        mb: 1,
        borderRadius: 1.25,
        border: (theme) => `solid 1px ${theme.palette.divider}`,
      }}
    >
      <Box className="flex-row align-center" sx={{ overflow: "hidden" }}>
        {getPreview()}
        <Box sx={{ ml: 2, overflow: "hidden" }}>
          <Typography noWrap={true} variant="body1">
            {name}
          </Typography>
          <Typography color="text.secondary" variant="caption">
            {formatFileSize(file.size)}
          </Typography>
        </Box>
      </Box>
      <IconButton
        aria-label="file-thumbnail-delete-button"
        onClick={() => props.onReplace?.()}
      >
        <ChangeCircleOutlinedIcon fontSize="small" color="action" />
      </IconButton>
    </Box>
  );
}
