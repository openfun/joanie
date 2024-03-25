import CloseIcon from "@mui/icons-material/Close";
import { closeSnackbar, SnackbarKey } from "notistack";
import * as React from "react";

export function CloseNotificationButton(key: SnackbarKey) {
  return (
    <CloseIcon
      data-testid="close-notification"
      fontSize="small"
      sx={{ cursor: "pointer" }}
      onClick={() => closeSnackbar(key)}
    />
  );
}
