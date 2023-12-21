import { render, screen } from "@testing-library/react";
import Button from "@mui/material/Button";
import userEvent from "@testing-library/user-event";
import TuneIcon from "@mui/icons-material/Tune";
import { MenuPopover } from "@/components/presentational/menu-popover/MenuPopover";
import { noop } from "@/utils";

describe("<MenuPopover />", () => {
  function TestMenu() {
    return (
      <MenuPopover
        button={<Button>Open</Button>}
        menuItems={[
          { title: "One", onClick: noop, icon: <TuneIcon /> },
          { title: "Two" },
        ]}
        arrow="right-top"
      />
    );
  }
  it("renders a MenuPopover component ", async () => {
    const user = userEvent.setup();
    render(<TestMenu />);
    const openButton = await screen.findByText("Open");
    await user.click(openButton);
    await screen.getByText("One");
    await screen.getByText("Two");
  });
});
