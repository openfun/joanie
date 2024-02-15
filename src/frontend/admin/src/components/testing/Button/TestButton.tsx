import { useState } from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import Button from "@mui/material/Button";
import { CustomModal } from "@/components/presentational/modal/Modal";
import { useModal } from "@/components/presentational/modal/useModal";

export function TestButton() {
  const [str, setStr] = useState("Oui");
  const modal = useModal();
  return (
    <Box>
      <Typography>{str}</Typography>
      <Button
        variant="outlined"
        color="secondary"
        onClick={() => {
          setStr(str === "Oui" ? "Non" : "Oui");
          modal.handleOpen();
        }}
      >
        Switch
      </Button>
      <CustomModal
        fullWidth={true}
        maxWidth="lg"
        title="Modal title"
        {...modal}
      >
        Test modal
      </CustomModal>
    </Box>
  );
}
