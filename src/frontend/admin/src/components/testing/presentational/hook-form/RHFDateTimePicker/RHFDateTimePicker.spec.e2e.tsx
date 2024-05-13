import { expect, test } from "@playwright/experimental-ct-react";
import { RHFDateTimePickerTestWrapper } from "@/components/testing/presentational/hook-form/RHFDateTimePicker/RHFDateTimePickerTestWrapper";

test.describe("<RHFDateTimePicker/>", () => {
  test("Check the message displayed when you delete part of the date with the keyboard", async ({
    mount,
    page,
  }) => {
    const component = await mount(<RHFDateTimePickerTestWrapper />);
    await component
      .locator("div")
      .filter({ hasText: /^End$/ })
      .getByLabel("Choose date")
      .click();
    await page.getByRole("gridcell", { name: "16" }).click();
    await page.getByRole("button", { name: "OK" }).click();
    await component.getByLabel("End", { exact: true }).click();
    await page.keyboard.press("ArrowRight");
    await page.keyboard.press("Backspace");
    await expect(component.getByText("Invalid date")).toBeVisible();
  });
});
