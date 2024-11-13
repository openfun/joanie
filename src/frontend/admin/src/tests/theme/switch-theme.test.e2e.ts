import { expect, test } from "@playwright/test";
import { PATH_ADMIN } from "@/utils/routes/path";

test.describe("UI Theme", () => {
  test("Switch of UI Theme", async ({ page }) => {
    await page.goto(PATH_ADMIN.rootAdmin);

    // A menu to switch of color scheme should be displayed
    const $button = await page.getByRole("button", {
      name: "Open color schemes menu",
    });
    expect($button).toBeVisible();
    await $button.click();

    // One menu item per theme mode should be displayed
    expect(await page.getByRole("menuitem", { name: "Light" })).toBeVisible();
    expect(await page.getByRole("menuitem", { name: "Dark" })).toBeVisible();
    expect(await page.getByRole("menuitem", { name: "System" })).toBeVisible();

    // Click on an item should close the menu and set the theme to the corresponding mode
    const $darkMenuItem = await page.getByRole("menuitem", { name: "Dark" });
    await $darkMenuItem.click();

    expect($darkMenuItem).not.toBeVisible();
    expect(
      await page.getByRole("menuitem", { name: "Light" }),
    ).not.toBeVisible();
    expect(
      await page.getByRole("menuitem", { name: "System" }),
    ).not.toBeVisible();

    let storageState = await page.context().storageState();
    let localstorage = storageState.origins[0].localStorage;
    expect(
      localstorage.find((entry) => {
        return entry.name === "mui-mode" && entry.value === "dark";
      }),
    ).toBeDefined();

    // Now switch to the system mode
    await $button.click();
    const $systemMenuItem = await page.getByRole("menuitem", {
      name: "System",
    });
    await $systemMenuItem.click();

    storageState = await page.context().storageState();
    localstorage = storageState.origins[0].localStorage;
    expect(
      localstorage.find((entry) => {
        return entry.name === "mui-mode" && entry.value === "system";
      }),
    ).toBeDefined();
  });
});
