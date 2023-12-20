import * as React from "react";
import { ReactNode } from "react";
import Box from "@mui/material/Box";
import IconButton from "@mui/material/IconButton";
import Typography from "@mui/material/Typography";
import { grey } from "@mui/material/colors";
import DeleteOutlineRoundedIcon from "@mui/icons-material/DeleteOutlineRounded";
import ModeEditOutlineTwoToneIcon from "@mui/icons-material/ModeEditOutlineTwoTone";

export interface DndDefaultRowProps {
  mainTitle: string | ReactNode;
  subTitle?: string | ReactNode;
  rightActions?: React.ReactNode;
  permanentRightActions?: React.ReactNode;
  enableEdit?: boolean;
  enableDelete?: boolean;
  onEdit?: () => void;
  onDelete?: () => void;
}

export function DndDefaultRow({
  enableDelete = true,
  enableEdit = false,
  ...props
}: DndDefaultRowProps) {
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
          ".right-actions": {
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
        sx={{
          display: "flex",
          alignItems: "center",
        }}
      >
        <Box
          className="right-actions"
          sx={{
            opacity: 0,
            display: "flex",
            justifyContent: "flex-end",
            gap: "5px",
            alignItems: "center",
          }}
        >
          {props.rightActions}
          {enableEdit && (
            <IconButton size="small" onClick={props.onEdit}>
              <ModeEditOutlineTwoToneIcon color="action" fontSize="small" />
            </IconButton>
          )}
          {enableDelete && (
            <IconButton size="small" onClick={props.onDelete}>
              <DeleteOutlineRoundedIcon color="error" fontSize="small" />
            </IconButton>
          )}
        </Box>
        <Box
          sx={{
            display: "flex",
            justifyContent: "flex-end",
            gap: "5px",
            alignItems: "center",
          }}
        >
          {props.permanentRightActions}
        </Box>
      </Box>
    </Box>
  );
}
