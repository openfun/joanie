import * as React from "react";
import { ReactNode } from "react";
import Box from "@mui/material/Box";
import IconButton from "@mui/material/IconButton";
import Typography from "@mui/material/Typography";
import DeleteOutlineRoundedIcon from "@mui/icons-material/DeleteOutlineRounded";
import ModeEditOutlineTwoToneIcon from "@mui/icons-material/ModeEditOutlineTwoTone";
import { useTheme } from "@mui/material/styles";

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
  const theme = useTheme();
  return (
    <Box
      display="flex"
      justifyContent="space-between"
      alignItems="center"
      sx={{
        px: 2,
        py: 1,
        borderRadius: 1,
        "&:hover": {
          ".right-actions": {
            opacity: 1,
          },
        },
        backgroundColor: theme.palette.grey[100],
        ...theme.applyStyles("dark", {
          backgroundColor: theme.palette.grey[700],
        }),
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
