import { expect, test } from "@playwright/experimental-ct-react";
import { Maybe } from "@/types/utils";
import { TranslatableForm } from "@/components/presentational/translatable-content/TranslatableForm";
import TranslatableFormProvider from "@/contexts/i18n/TranslatableFormProvider";

test.describe("<TranslatableForm/>", () => {
  test("Check onSelectLang call", async ({ mount }) => {
    let lang: Maybe<string> = "";
    const component = await mount(
      <TranslatableFormProvider>
        <TranslatableForm onSelectLang={(newLang) => (lang = newLang)}>
          John Doe
        </TranslatableForm>
      </TranslatableFormProvider>,
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
      <TranslatableFormProvider>
        <TranslatableForm onSelectLang={() => {}}>John Doe</TranslatableForm>
      </TranslatableFormProvider>,
    );
    await component.waitFor({ state: "attached" });

    let states = await page.context().storageState();
    let storage = states.origins[0].localStorage;
    expect(
      storage.some(
        (entry) =>
          entry.name === "translateContentLanguage" && entry.value === "en-us",
      ),
    ).toBe(true);
    expect(
      storage.some(
        (entry) =>
          entry.name === "django_language_saved" && entry.value === "en-us",
      ),
    ).toBe(true);

    await component.getByRole("tab", { name: "French" }).click();
    states = await page.context().storageState();
    storage = states.origins[0].localStorage;
    expect(
      storage.some(
        (entry) =>
          entry.name === "translateContentLanguage" && entry.value === "fr-fr",
      ),
    ).toBe(true);
    expect(
      storage.some(
        (entry) =>
          entry.name === "django_language_saved" && entry.value === "en-us",
      ),
    ).toBe(true);
  });

  test("Check local storage values with several translatable forms", async ({
    mount,
    page,
  }) => {
    // Until there is a TranslatableForm mounted, language settings should be saved
    // into the localstorage, then when all the stuff is unmounted, the cookie `django_language`
    // should be restored.

    let mountedForms = [true, true];
    // Mount both TranslatableForms
    const component = await mount(
      <TranslatableFormProvider>
        {mountedForms[0] === true && (
          <TranslatableForm onSelectLang={() => {}} />
        )}
        {mountedForms[1] === true && (
          <TranslatableForm onSelectLang={() => {}} />
        )}
      </TranslatableFormProvider>,
    );
    await component.waitFor({ state: "attached" });

    let states = await page.context().storageState();
    let storage = states.origins[0].localStorage;
    expect(
      storage.some(
        (entry) =>
          entry.name === "translateContentLanguage" && entry.value === "en-us",
      ),
    ).toBe(true);
    expect(
      storage.some(
        (entry) =>
          entry.name === "django_language_saved" && entry.value === "en-us",
      ),
    ).toBe(true);
    let cookie = states.cookies.find(
      (entry) => entry.name === "django_language",
    );
    expect(cookie).toBe(undefined);

    // Only unmount one TranslatableForm
    mountedForms = [false, true];
    // Mount both TranslatableForms
    await component.update(
      <TranslatableFormProvider>
        {mountedForms[0] === true && (
          <TranslatableForm onSelectLang={() => {}} />
        )}
        {mountedForms[1] === true && (
          <TranslatableForm onSelectLang={() => {}} />
        )}
      </TranslatableFormProvider>,
    );
    states = await page.context().storageState();
    storage = states.origins[0].localStorage;
    expect(
      storage.some(
        (entry) =>
          entry.name === "translateContentLanguage" && entry.value === "en-us",
      ),
    ).toBe(true);
    expect(
      storage.some(
        (entry) =>
          entry.name === "django_language_saved" && entry.value === "en-us",
      ),
    ).toBe(true);
    cookie = states.cookies.find((entry) => entry.name === "django_language");
    expect(cookie).toBe(undefined);

    // Unmount both TranslatableForms
    mountedForms = [false, false];
    await component.update(
      <TranslatableFormProvider>
        {mountedForms[0] === true && (
          <TranslatableForm onSelectLang={() => {}} />
        )}
        {mountedForms[1] === true && (
          <TranslatableForm onSelectLang={() => {}} />
        )}
      </TranslatableFormProvider>,
    );
    states = await page.context().storageState();
    expect(states.origins.length).toBe(0);
    cookie = states.cookies.find((entry) => entry.name === "django_language");
    expect(cookie).toBeDefined();
    expect(cookie!.value).toBe("en-us");
  });

  test("Check that the loader is displayed", async ({ mount }) => {
    const component = await mount(
      <TranslatableFormProvider>
        <TranslatableForm isLoading={true} onSelectLang={() => {}}>
          John Doe
        </TranslatableForm>
      </TranslatableFormProvider>,
    );

    await expect(component.getByRole("progressbar")).toBeVisible();
  });
});
