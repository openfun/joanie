import { expect, test } from "@playwright/experimental-ct-react";
import { TestButton } from "@/components/testing/Button/TestButton";

test("should work", async ({ mount, page }) => {
  await page.route("/toto", () => "toto");
  const component = await mount(<TestButton />);
  await expect(component).toContainText("Oui");
  await component.getByRole("button").click();
  await expect(component).toContainText("Non");
  await expect(
    page.getByRole("heading", { name: "Modal title" }),
  ).toBeVisible();

  await expect(page.getByTestId("custom-modal")).toBeVisible();
  // await expect(component.getByTestId("custom-modal")).toBeVisible();
});
