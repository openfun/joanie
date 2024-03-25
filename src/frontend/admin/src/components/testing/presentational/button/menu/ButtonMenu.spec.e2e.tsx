import { expect, test } from "@playwright/experimental-ct-react";
import CancelIcon from "@mui/icons-material/Cancel";
import { AccountBox } from "@mui/icons-material";
import ButtonMenu, {
  MenuOption,
} from "@/components/presentational/button/menu/ButtonMenu";

test.describe("<ButtonMenu/>", () => {
  test("Check if all the main labels are present", async ({ mount, page }) => {
    const options = [
      { mainLabel: "Create" },
      { mainLabel: "Update" },
      { mainLabel: "Delete" },
    ];
    const component = await mount(
      <div>
        <ButtonMenu label="Actions" id="test-button-menu" options={options} />
      </div>,
    );

    // Check if button is present with his arrow
    await expect(
      component.getByRole("button", { name: "Actions" }),
    ).toBeVisible();
    await expect(
      component
        .getByRole("button", { name: "Actions" })
        .getByTestId("KeyboardArrowDownIcon"),
    ).toBeVisible();

    await component.getByRole("button", { name: "Actions" }).click();
    await Promise.all(
      options.map(async (option) => {
        await expect(
          page.getByRole("menuitem", { name: option.mainLabel }),
        ).toBeVisible();
      }),
    );
  });

  test("Check if all the icons are present", async ({ mount, page }) => {
    const options: MenuOption[] = [
      { mainLabel: "Cancel", icon: <CancelIcon /> },
      { mainLabel: "Account", icon: <AccountBox /> },
    ];
    const component = await mount(
      <div>
        <ButtonMenu label="Actions" id="test-button-menu" options={options} />
      </div>,
    );

    await component.getByRole("button", { name: "Actions" }).click();
    await expect(
      page.getByRole("menuitem", { name: "Cancel" }).getByTestId("CancelIcon"),
    ).toBeVisible();
    await expect(
      page
        .getByRole("menuitem", { name: "Account" })
        .getByTestId("AccountBoxIcon"),
    ).toBeVisible();
  });

  test("Check if all the right labels with react element are present", async ({
    mount,
    page,
  }) => {
    const options: MenuOption[] = [
      { mainLabel: "Cancel", rightLabel: <CancelIcon /> },
      { mainLabel: "Account", rightLabel: <AccountBox /> },
    ];
    const component = await mount(
      <div>
        <ButtonMenu label="Actions" id="test-button-menu" options={options} />
      </div>,
    );
    await component.getByRole("button", { name: "Actions" }).click();
    await expect(
      page.getByRole("menuitem", { name: "Cancel" }).getByTestId("CancelIcon"),
    ).toBeVisible();
    await expect(
      page
        .getByRole("menuitem", { name: "Account" })
        .getByTestId("AccountBoxIcon"),
    ).toBeVisible();
  });

  test("Check if all the right labels with string are present", async ({
    mount,
    page,
  }) => {
    const options: MenuOption[] = [
      { mainLabel: "Cancel", rightLabel: "C" },
      { mainLabel: "Account", rightLabel: "A" },
    ];
    const component = await mount(
      <div>
        <ButtonMenu label="Actions" id="test-button-menu" options={options} />
      </div>,
    );
    await component.getByRole("button", { name: "Actions" }).click();
    await expect(
      page
        .getByRole("menuitem", { name: "Cancel" })
        .getByText("C", { exact: true }),
    ).toBeVisible();
    await expect(
      page
        .getByRole("menuitem", { name: "Account" })
        .getByText("A", { exact: true }),
    ).toBeVisible();
  });

  test("Check if the onClick props is called", async ({ mount, page }) => {
    let cancelClicked = false;
    const options: MenuOption[] = [
      {
        mainLabel: "Cancel",
        onClick: () => {
          cancelClicked = true;
        },
      },
      { mainLabel: "Account" },
    ];
    const component = await mount(
      <div>
        <ButtonMenu label="Actions" id="test-button-menu" options={options} />
      </div>,
    );

    expect(cancelClicked).toEqual(false);
    await component.getByRole("button", { name: "Actions" }).click();
    await page.getByRole("menuitem", { name: "Cancel" }).click();
    expect(cancelClicked).toEqual(true);
  });

  test("Check when an option is not disabled, its message is not displayed on hover", async ({
    mount,
    page,
  }) => {
    const cancelClicked = false;
    const options: MenuOption[] = [
      {
        mainLabel: "Cancel",
        isDisable: false,
        disableMessage: "John doe",
      },
      { mainLabel: "Account" },
    ];
    const component = await mount(
      <div>
        <ButtonMenu label="Actions" id="test-button-menu" options={options} />
      </div>,
    );

    expect(cancelClicked).toEqual(false);
    await component.getByRole("button", { name: "Actions" }).click();
    await page.getByTestId("Cancel").hover();
    await expect(page.getByText("John Doe")).not.toBeVisible();
  });

  test("Check when an option is disabled, its message is displayed on hover", async ({
    mount,
    page,
  }) => {
    const cancelClicked = false;
    const options: MenuOption[] = [
      {
        mainLabel: "Cancel",
        isDisable: true,
        disableMessage: "John doe",
      },
      { mainLabel: "Account" },
    ];
    const component = await mount(
      <div>
        <ButtonMenu label="Actions" id="test-button-menu" options={options} />
      </div>,
    );

    expect(cancelClicked).toEqual(false);
    await component.getByRole("button", { name: "Actions" }).click();
    await page.getByTestId("Cancel").hover();
    await expect(page.getByText("John Doe")).toBeVisible();
  });
});
