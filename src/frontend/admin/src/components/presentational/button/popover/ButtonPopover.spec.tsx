import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import TuneIcon from "@mui/icons-material/Tune";
import * as React from "react";
import IconButton from "@mui/material/IconButton";
import Button from "@mui/material/Button";
import ButtonPopover from "@/components/presentational/button/popover/ButtonPopover";

describe("<ButtonPopover />", () => {
  it("renders without icon", async () => {
    render(
      <ButtonPopover button={<Button variant="contained">Open</Button>}>
        <div>John Doe</div>
      </ButtonPopover>,
    );

    const button = await screen.findByRole("button", { name: "Open" });
    expect(screen.queryByTestId("IconPopoverButton")).toBe(null);
    await userEvent.click(button);
    screen.getByText("John Doe");
  });

  it("renders with icon", async () => {
    render(
      <ButtonPopover
        button={
          <IconButton>
            <TuneIcon color="primary" />
          </IconButton>
        }
      >
        <div>John Doe</div>
      </ButtonPopover>,
    );

    const button = await screen.findByTestId("PopoverButton");
    await userEvent.click(button);
    screen.getByText("John Doe");
  });
});
