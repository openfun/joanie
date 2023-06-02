import { render, screen } from "@testing-library/react";
import Button from "@mui/material/Button";
import ListItemText from "@mui/material/ListItemText";
import MenuItem from "@mui/material/MenuItem";
import MenuList from "@mui/material/MenuList";
import userEvent from "@testing-library/user-event";
import {
  MenuPopover,
  useMenuPopover,
} from "@/components/presentational/menu-popover/MenuPopover";

describe("<MenuPopover />", () => {
  function TestMenu() {
    const menu = useMenuPopover();
    return (
      <>
        <Button onClick={menu.open}>Open</Button>
        <MenuPopover open={menu.anchor} onClose={menu.close} arrow="right-top">
          <MenuList>
            <MenuItem>
              <ListItemText>One</ListItemText>
            </MenuItem>
            <MenuItem>
              <ListItemText>Two</ListItemText>
            </MenuItem>
          </MenuList>
        </MenuPopover>
      </>
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
