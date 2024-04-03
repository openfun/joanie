import { expect, test } from "@playwright/test";
import { PATH_ADMIN } from "@/utils/routes/path";

test.describe("Internationalization", () => {
  test("Switch from English to French", async ({ page }) => {
    await page.goto(PATH_ADMIN.rootAdmin);

    // English
    await expect(
      page.getByRole("heading", { name: "Joanie administration" }),
    ).toBeVisible();
    await expect(page.getByText("Home page")).toBeVisible();
    let cookies = await page.context().cookies();
    expect(cookies.length).toEqual(0);

    // Switch to french
    await page.getByTestId("select-language").click();
    await page.getByRole("option", { name: "Français" }).click();
    cookies = await page.context().cookies();
    expect(cookies.length).toEqual(1);
    let djangoLanguage = cookies[0];
    expect(djangoLanguage.name).toEqual("django_language");
    expect(djangoLanguage.value).toEqual("fr-fr");

    // French
    await expect(
      page.getByRole("heading", { name: "Administration de Joanie" }),
    ).toBeVisible();
    await expect(page.getByText("Page d’accueil")).toBeVisible();

    await page.getByTestId("select-language").click();
    await page.getByRole("option", { name: "English" }).click();
    cookies = await page.context().cookies();
    // eslint-disable-next-line prefer-destructuring
    djangoLanguage = cookies[0];
    expect(djangoLanguage.name).toEqual("django_language");
    expect(djangoLanguage.value).toEqual("en-us");

    // English
    await expect(
      page.getByRole("heading", { name: "Joanie administration" }),
    ).toBeVisible();
    await expect(page.getByText("Home page")).toBeVisible();
  });
});
