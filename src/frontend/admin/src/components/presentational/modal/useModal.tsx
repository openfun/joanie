import { useState } from "react";

export const useModal = () => {
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
