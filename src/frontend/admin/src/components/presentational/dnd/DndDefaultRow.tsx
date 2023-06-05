import * as React from "react";
import Box from "@mui/material/Box";
import IconButton from "@mui/material/IconButton";
import Typography from "@mui/material/Typography";
import { grey } from "@mui/material/colors";
import DeleteOutlineRoundedIcon from "@mui/icons-material/DeleteOutlineRounded";

interface Props {
  mainTitle: string;
  subTitle?: string;
  rightActions?: React.ReactNode;
  onDelete?: () => void;
}

export function DndDefaultRow(props: Props) {
  return (
    <Box
      display="flex"
      justifyContent="space-between"
      alignItems="center"
      sx={{
        px: 2,
        py: 1,
        borderRadius: 1,
        backgroundColor: grey[100],
        "&:hover": {
          ".toto-test": {
            opacity: 1,
          },
        },
      }}
    >
      <Box>
        <Typography variant="subtitle2">{props.mainTitle}</Typography>
        <Typography variant="caption">{props.subTitle}</Typography>
      </Box>
      <Box
        className="toto-test"
        sx={{
          opacity: 0,
          display: "flex",
          justifyContent: "flex-end",
          gap: "5px",
          alignItems: "center",
        }}
      >
        {props.rightActions}
        <IconButton size="small" onClick={props.onDelete}>
          <DeleteOutlineRoundedIcon color="error" fontSize="small" />
        </IconButton>
      </Box>
    </Box>
  );
}
