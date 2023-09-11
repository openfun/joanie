import Popover from "@mui/material/Popover";
import * as React from "react";
import {
  MouseEvent,
  PropsWithChildren,
  ReactElement,
  useMemo,
  useState,
} from "react";

type Props = {
  button: ReactElement;
};

export default function ButtonPopover(props: PropsWithChildren<Props>) {
  const [anchorEl, setAnchorEl] = useState<HTMLButtonElement | null>(null);

  const handleClick = (event: MouseEvent<HTMLButtonElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleClose = () => {
    setAnchorEl(null);
  };

  const open = Boolean(anchorEl);
  const id = open ? "ButtonPopover" : undefined;

  const button = useMemo(() => {
    return React.cloneElement(props.button, {
      onClick: handleClick,
      "data-testid": "PopoverButton",
      "aria-describedby": id,
    });
  }, [props.button]);

  return (
    <div>
      {button}
      <Popover
        id={id}
        open={open}
        anchorEl={anchorEl}
        onClose={handleClose}
        anchorOrigin={{
          vertical: "bottom",
          horizontal: "left",
        }}
      >
        {props.children}
      </Popover>
    </div>
  );
}
