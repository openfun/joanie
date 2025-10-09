import { expect, test } from "@playwright/test";
import { mockPlaywrightCrud } from "@/tests/useResourceHandler";
import { getQuoteDefinitionScenarioStore } from "@/tests/quote-definitions/QuoteDefinitionTestScenario";
import {
  QuoteDefinition,
  DTOQuoteDefinition,
} from "@/services/api/models/QuoteDefinition";
import { PATH_ADMIN } from "@/utils/routes/path";
import { QUOTE_DEFINITION_OPTIONS_REQUEST_RESULT } from "@/tests/mocks/quote-definitions/quote-definition-mocks";

const quoteDefinitionApiUrl =
  "http://localhost:8071/api/v1.0/admin/quote-definitions/";

test.describe("Quote definition filters", () => {
  let store = getQuoteDefinitionScenarioStore();

  test.beforeEach(async ({ page }) => {
    store = getQuoteDefinitionScenarioStore();
    await mockPlaywrightCrud<QuoteDefinition, DTOQuoteDefinition>({
      data: store.list,
      routeUrl: quoteDefinitionApiUrl,
      page,
      searchResult: store.list[1],
      optionsResult: QUOTE_DEFINITION_OPTIONS_REQUEST_RESULT,
    });
  });

  test("Test that filters apply", async ({ page }) => {
    await page.goto(PATH_ADMIN.quote_definition.list);
    await expect(
      page.getByRole("heading", { name: "Quote definitions" }),
    ).toBeVisible();

    await Promise.all(
      store.list.map(async (quote) => {
        await expect(page.getByText(quote.title)).toBeVisible();
      }),
    );

    await page.getByRole("button", { name: "Filters" }).click();
    await expect(page.getByRole("heading", { name: "filters" })).toBeVisible();
    const selectLangLocator = page
      .getByTestId("quote-definition-language-input")
      .getByLabel("Language");
    await expect(selectLangLocator).toBeVisible();
    await expect(page.locator(`[name='language']`)).toHaveValue("");
    await selectLangLocator.click();

    await expect(page.getByRole("option", { name: "English" })).toBeVisible();
    await expect(page.getByRole("option", { name: "French" })).toBeVisible();

    const filterResult = [store.list[0], store.list[1]];
    await mockPlaywrightCrud<QuoteDefinition, DTOQuoteDefinition>({
      data: store.list,
      routeUrl: quoteDefinitionApiUrl,
      page,
      searchResult: filterResult,
      forceFiltersMode: true,
      optionsResult: QUOTE_DEFINITION_OPTIONS_REQUEST_RESULT,
    });

    await page.getByRole("option", { name: "French" }).click();
    await expect(page.locator(`[name='language']`)).toHaveValue("fr-fr");
    await page.getByLabel("close").click();

    await Promise.all(
      filterResult.map(async (quote) => {
        await expect(page.getByText(quote.title)).toBeVisible();
      }),
    );

    await expect(page.getByText(store.list[2].title)).toBeHidden();

    await expect(
      page.getByRole("button", { name: "Language: French" }),
    ).toBeVisible();
    await expect(page.getByRole("button", { name: "Clear" })).toBeVisible();
    await page.getByRole("button", { name: "Filters" }).click();
    await expect(page.getByLabel("French")).toBeVisible();
    await page.getByLabel("close").click();

    await mockPlaywrightCrud<QuoteDefinition, DTOQuoteDefinition>({
      data: store.list,
      routeUrl: quoteDefinitionApiUrl,
      page,
      searchResult: filterResult,
      forceFiltersMode: false,
      optionsResult: QUOTE_DEFINITION_OPTIONS_REQUEST_RESULT,
    });
    await page.getByRole("button", { name: "Language: French" }).click();
    await page.getByRole("button", { name: "Clear" }).click();

    await Promise.all(
      store.list.map(async (quote) => {
        await expect(page.getByText(quote.title)).toBeVisible();
      }),
    );
    await page.getByRole("button", { name: "Filters" }).click();
    await expect(selectLangLocator).toBeVisible();
    await expect(page.locator(`[name='language']`)).toHaveValue("");
  });
});
