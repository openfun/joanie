import { useState } from "react";

export interface ModalUtils {
  open: boolean;
  handleOpen: () => void;
  handleClose: () => void;
  toggleModal: () => void;
}
export const useModal = (): ModalUtils => {
  const [open, setOpen] = useState(false);

  const handleOpen = (): void => {
    setOpen(true);
  };

  const handleClose = (): void => {
    setOpen(false);
  };

  const toggleModal = (): void => {
    setOpen(!open);
  };

  return {
    open,
    handleOpen,
    handleClose,
    toggleModal,
  };
};
