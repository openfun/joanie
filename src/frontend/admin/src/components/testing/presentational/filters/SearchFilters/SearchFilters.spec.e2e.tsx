import { expect, test } from "@playwright/experimental-ct-react";
import { Page } from "@playwright/test";
import { SearchFiltersWrapperTest } from "@/components/testing/presentational/filters/SearchFilters/SearchFiltersWrapperTest";

const selectInputs = async (page: Page) => {
  await page.getByLabel("Yes").check();
  await page.getByLabel("Language").click();
  await page.getByRole("option", { name: "French" }).click();
  await page.getByLabel("User").click();
  await page.getByTestId("custom-modal").getByLabel("User").fill("jo");
  await page.getByRole("option", { name: "John Doe" }).click();
};

test.describe("<SearchFilters/>", () => {
  test("Check heading and alert text", async ({ mount, page }) => {
    const component = await mount(<SearchFiltersWrapperTest />);
    await component.getByRole("button", { name: "Filters" }).click();
    await expect(
      page.getByRole("heading", { name: "Add filters" }),
    ).toBeVisible();
    await expect(
      page
        .getByRole("alert")
        .getByText(
          'In this part, you can add filters to filter entities based on different parameters. On a multiple choice filter, an "OR" is applied',
        ),
    ).toBeVisible();
  });

  test("Check the pills display with the different compatible input types", async ({
    mount,
    page,
  }) => {
    const component = await mount(<SearchFiltersWrapperTest />);
    await component.getByRole("button", { name: "Filters" }).click();
    await selectInputs(page);
    await page.getByLabel("close").click();
    await expect(
      component.getByRole("button", { name: "Enable: yes" }),
    ).toBeVisible();
    await expect(
      component.getByRole("button", { name: "Language: fr" }),
    ).toBeVisible();
    await expect(
      component.getByRole("button", { name: "User: John Doe" }),
    ).toBeVisible();
    await expect(
      component.getByRole("button", { name: "Clear" }),
    ).toBeVisible();
  });

  test("Remove filters and check form input values", async ({
    mount,
    page,
  }) => {
    const component = await mount(<SearchFiltersWrapperTest />);
    await component.getByRole("button", { name: "Filters" }).click();
    await selectInputs(page);
    expect(await page.getByTestId("select-value").inputValue()).toEqual("fr");
    expect(await page.getByLabel("Yes").isChecked()).toEqual(true);
    expect(await page.getByLabel("None").isChecked()).toEqual(false);
    expect(
      await page
        .getByTestId("autocomplete-test")
        .getByRole("combobox")
        .inputValue(),
    ).toEqual("John Doe");
    await page.getByLabel("close").click();

    // Checkbox
    await component
      .getByRole("button", { name: "Enable: yes" })
      .getByTestId("CancelIcon")
      .click();

    // Select
    await component
      .getByRole("button", { name: "Language: fr" })
      .getByTestId("CancelIcon")
      .click();

    // Autocomplete
    await component
      .getByRole("button", { name: "User: John Doe" })
      .getByTestId("CancelIcon")
      .click();

    // Check all value
    await component.getByRole("button", { name: "Filters" }).click();
    expect(await page.getByLabel("Yes").isChecked()).toEqual(false);
    expect(await page.getByLabel("None").isChecked()).toEqual(true);
    expect(await page.getByTestId("select-value").inputValue()).toEqual("");
    expect(
      await page
        .getByTestId("autocomplete-test")
        .getByRole("combobox")
        .inputValue(),
    ).toEqual("");
  });

  test("Click on clear button and check form input values", async ({
    mount,
    page,
  }) => {
    const component = await mount(<SearchFiltersWrapperTest />);
    await component.getByRole("button", { name: "Filters" }).click();
    await selectInputs(page);
    expect(await page.getByTestId("select-value").inputValue()).toEqual("fr");
    expect(await page.getByLabel("Yes").isChecked()).toEqual(true);
    expect(await page.getByLabel("None").isChecked()).toEqual(false);
    expect(
      await page
        .getByTestId("autocomplete-test")
        .getByRole("combobox")
        .inputValue(),
    ).toEqual("John Doe");
    await page.getByLabel("close").click();
    await page.getByRole("button", { name: "Clear" }).click();

    // Check all value
    await component.getByRole("button", { name: "Filters" }).click();
    expect(await page.getByLabel("Yes").isChecked()).toEqual(false);
    expect(await page.getByLabel("None").isChecked()).toEqual(true);
    expect(await page.getByTestId("select-value").inputValue()).toEqual("");
    expect(
      await page
        .getByTestId("autocomplete-test")
        .getByRole("combobox")
        .inputValue(),
    ).toEqual("");
  });
});
