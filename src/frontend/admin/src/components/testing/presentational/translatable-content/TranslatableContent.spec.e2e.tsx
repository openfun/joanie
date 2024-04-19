import { expect, test } from "@playwright/experimental-ct-react";
import { Maybe } from "@/types/utils";
import { TranslatableForm } from "@/components/presentational/translatable-content/TranslatableForm";

test.describe("<TranslatableForm/>", () => {
  test("Check onSelectLang call", async ({ mount }) => {
    let lang: Maybe<string> = "";
    const component = await mount(
      <TranslatableForm onSelectLang={(newLang) => (lang = newLang)}>
        John Doe
      </TranslatableForm>,
    );
    await expect(component.getByText("John Doe")).toBeVisible();
    expect(lang).toEqual("");
    await component.getByRole("tab", { name: "French" }).click();
    expect(lang).toEqual("fr-fr");
    await component.getByRole("tab", { name: "English" }).click();
    expect(lang).toEqual("en-us");
  });

  test("Check local storage values", async ({ mount, page }) => {
    const component = await mount(
      <TranslatableForm onSelectLang={() => {}}>John Doe</TranslatableForm>,
    );

    let states = await page.context().storageState();
    let storage = states.origins[0].localStorage;
    expect(storage).toEqual([
      { name: "translateContentLanguage", value: "en-us" },
      { name: "django_language_saved", value: "en-us" },
    ]);

    await component.getByRole("tab", { name: "French" }).click();
    states = await page.context().storageState();
    storage = states.origins[0].localStorage;
    expect(storage).toEqual([
      { name: "translateContentLanguage", value: "fr-fr" },
      { name: "django_language_saved", value: "en-us" },
    ]);
  });

  test("Check that the loader is displayed", async ({ mount }) => {
    const component = await mount(
      <TranslatableForm isLoading={true} onSelectLang={() => {}}>
        John Doe
      </TranslatableForm>,
    );

    await expect(component.getByRole("progressbar")).toBeVisible();
  });
});
