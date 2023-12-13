import * as React from "react";
import { PropsWithChildren, ReactNode } from "react";
import Box from "@mui/material/Box";
import IconButton from "@mui/material/IconButton";
import Typography from "@mui/material/Typography";
import { grey } from "@mui/material/colors";
import DeleteOutlineRoundedIcon from "@mui/icons-material/DeleteOutlineRounded";
import ModeEditOutlineTwoToneIcon from "@mui/icons-material/ModeEditOutlineTwoTone";

import CircularProgress from "@mui/material/CircularProgress";
import { SxProps } from "@mui/material/styles";
import Tooltip from "@mui/material/Tooltip";

export interface DefaultRowProps {
  mainTitle: string;
  subTitle?: string | ReactNode;
  rightActions?: React.ReactNode;
  permanentRightActions?: React.ReactNode;
  enableEdit?: boolean;
  enableDelete?: boolean;
  disableDeleteMessage?: string;
  disableEditMessage?: string;
  testId?: string;
  onEdit?: () => void;
  loading?: boolean;
  onDelete?: () => void;
  deleteTestId?: string;
  sx?: SxProps;
}

export function DefaultRow({
  enableDelete = true,
  enableEdit = false,
  loading = false,
  onEdit,
  onDelete,
  ...props
}: PropsWithChildren<DefaultRowProps>) {
  return (
    <>
      <Box
        data-testid={props.testId}
        display="flex"
        justifyContent="space-between"
        alignItems="center"
        sx={{
          px: 2,
          py: 1,
          borderRadius: 1,
          backgroundColor: grey[100],
          border: `2px solid ${grey[100]}`,
          "&:hover": {
            ".right-actions": {
              opacity: 1,
            },
          },
          ...props.sx,
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

            <ButtonWithTooltip
              showButton={enableEdit}
              disableMessage={props.disableEditMessage}
            >
              <IconButton
                size="small"
                data-testid="edit-row-button"
                disabled={!enableEdit}
                onClick={onEdit}
              >
                <ModeEditOutlineTwoToneIcon color="action" fontSize="small" />
              </IconButton>
            </ButtonWithTooltip>
            <ButtonWithTooltip
              showButton={enableDelete}
              disableMessage={props.disableDeleteMessage}
            >
              <IconButton
                size="small"
                data-testid={props.deleteTestId ?? "delete-row-button"}
                disabled={!enableDelete}
                onClick={onDelete}
              >
                <DeleteOutlineRoundedIcon color="error" fontSize="small" />
              </IconButton>
            </ButtonWithTooltip>
          </Box>
          <Box
            sx={{
              display: "flex",
              justifyContent: "flex-end",
              gap: "5px",
              alignItems: "center",
            }}
          >
            {!loading && props.permanentRightActions}
            {loading && <CircularProgress size={16} />}
          </Box>
        </Box>
      </Box>
      {props.children && <Box paddingLeft={5}>{props.children}</Box>}
    </>
  );
}

type ActionButton = {
  disableMessage?: string;
  showButton: boolean;
};

function ButtonWithTooltip(props: PropsWithChildren<ActionButton>) {
  if (props.showButton) {
    return props.children;
  }

  if (!props.showButton && props.disableMessage) {
    return (
      <Tooltip arrow title={props.disableMessage}>
        <span>{props.children}</span>
      </Tooltip>
    );
  }

  return undefined;
}
