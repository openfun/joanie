import { expect, test } from "@playwright/experimental-ct-react";
import Button from "@mui/material/Button";
import { RHFProviderTestWrapper } from "@/components/testing/presentational/hook-form/RHFProvider/RHFProviderTestWrapper";

test.describe("<RHFProvider/>", () => {
  test("Check if on submit is called", async ({ mount }) => {
    const component = await mount(<RHFProviderTestWrapper />);
    await expect(
      component.getByTestId("name-value").getByText("Name: ", { exact: true }),
    ).toBeVisible();
    await component.getByLabel("Name", { exact: true }).fill("Doe");
    await component.getByRole("button", { name: "Submit" }).click();
    await expect(
      component
        .getByTestId("name-value")
        .getByText("Name: Doe", { exact: true }),
    ).toBeVisible();
  });

  test("Test if unsaved form modal appears on page change when checkBeforeUnload props is set to true", async ({
    mount,
    page,
  }) => {
    const component = await mount(
      <RHFProviderTestWrapper checkBeforeUnload={true} />,
    );
    await component.getByLabel("Name", { exact: true }).fill("Doe");
    await component.getByTestId("exit-link").click();
    const modal = page.getByTestId("unsaved-form-modal");
    await expect(
      modal.getByRole("heading", { name: "Before you leave!" }),
    ).toBeVisible();
  });

  test("Test if unsaved form modal appears on refresh page change when checkBeforeUnload props is set to true", async ({
    mount,
    page,
  }) => {
    const component = await mount(
      <RHFProviderTestWrapper checkBeforeUnload={true} />,
    );
    let hasDialog = false;
    page.on("dialog", async (dialog) => {
      await dialog.accept();
      hasDialog = true;
    });
    await component.getByLabel("Name", { exact: true }).fill("Doe");
    await page.reload();
    expect(hasDialog).toEqual(true);
  });

  test("Hide submit button", async ({ mount }) => {
    const component = await mount(
      <RHFProviderTestWrapper showSubmit={false} />,
    );
    await expect(component.getByRole("button", { name: "Submit" })).toHaveCount(
      0,
    );
  });

  test("Show loader on submit button", async ({ mount }) => {
    const component = await mount(
      <RHFProviderTestWrapper isSubmitting={true} />,
    );
    const submitButton = component.getByRole("button", { name: "Submit" });
    await expect(submitButton).toHaveCount(1);
    await expect(submitButton.getByRole("progressbar")).toHaveCount(1);
  });

  test("Show actions buttons", async ({ mount }) => {
    const component = await mount(
      <RHFProviderTestWrapper actionButtons={<Button>Click here !</Button>} />,
    );
    const button = component.getByRole("button", { name: "Click here !" });
    await expect(button).toHaveCount(1);
  });
});
