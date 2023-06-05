import * as React from "react";
import Box from "@mui/material/Box";
import IconButton from "@mui/material/IconButton";
import Typography from "@mui/material/Typography";
import { Close, FileOpen } from "@mui/icons-material";

interface Props {
  file: File;
  onDelete?: (file: File) => void;
}

export function FileThumbnail({ file, ...props }: Props) {
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

  return (
    <Box
      key={file.name}
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
      <div className="flex-row align-center">
        <FileOpen color="primary" />
        <Box sx={{ ml: 2 }}>
          <Typography variant="body1">{file.name}</Typography>
          <Typography color="text.secondary" variant="caption">
            {formatFileSize(file.size)}
          </Typography>
        </Box>
      </div>
      <IconButton
        aria-label="file-thumbnail-delete-button"
        onClick={() => props.onDelete?.(file)}
      >
        <Close fontSize="small" color="action" />
      </IconButton>
    </Box>
  );
}
