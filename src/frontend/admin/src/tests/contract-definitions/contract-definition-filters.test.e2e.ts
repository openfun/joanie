import { expect, test } from "@playwright/test";
import { mockPlaywrightCrud } from "@/tests/useResourceHandler";
import { getContractDefinitionScenarioStore } from "@/tests/contract-definitions/ContractDefinitionTestScenario";
import {
  ContractDefinition,
  DTOContractDefinition,
} from "@/services/api/models/ContractDefinition";
import { PATH_ADMIN } from "@/utils/routes/path";
import { CONTRACT_DEFINITION_OPTIONS_REQUEST_RESULT } from "@/tests/mocks/contract-definitions/contract-definition-mocks";

const contractDefinitionApiUrl =
  "http://localhost:8071/api/v1.0/admin/contract-definitions/";

test.describe("Contract definition filters", () => {
  let store = getContractDefinitionScenarioStore();

  test.beforeEach(async ({ page }) => {
    store = getContractDefinitionScenarioStore();
    await mockPlaywrightCrud<ContractDefinition, DTOContractDefinition>({
      data: store.list,
      routeUrl: contractDefinitionApiUrl,
      page,
      searchResult: store.list[1],
      optionsResult: CONTRACT_DEFINITION_OPTIONS_REQUEST_RESULT,
    });
  });

  test("Test that filters apply", async ({ page }) => {
    await page.goto(PATH_ADMIN.contract_definition.list);
    await expect(
      page.getByRole("heading", { name: "Contracts definitions" }),
    ).toBeVisible();

    await Promise.all(
      store.list.map(async (contract) => {
        await expect(page.getByText(contract.title)).toBeVisible();
      }),
    );

    await page.getByRole("button", { name: "Filters" }).click();
    await expect(page.getByRole("heading", { name: "filters" })).toBeVisible();
    const selectLangLocator = page
      .getByTestId("contract-definition-language-input")
      .getByLabel("Language");
    await expect(selectLangLocator).toBeVisible();
    await expect(page.locator(`[name='language']`)).toHaveValue("");
    await selectLangLocator.click();

    await expect(page.getByRole("option", { name: "English" })).toBeVisible();
    await expect(page.getByRole("option", { name: "French" })).toBeVisible();

    const filterResult = [store.list[0], store.list[1]];
    await mockPlaywrightCrud<ContractDefinition, DTOContractDefinition>({
      data: store.list,
      routeUrl: contractDefinitionApiUrl,
      page,
      searchResult: filterResult,
      forceFiltersMode: true,
      optionsResult: CONTRACT_DEFINITION_OPTIONS_REQUEST_RESULT,
    });

    await page.getByRole("option", { name: "French" }).click();
    await expect(page.locator(`[name='language']`)).toHaveValue("fr-fr");
    await page.getByLabel("close").click();

    await Promise.all(
      filterResult.map(async (contract) => {
        await expect(page.getByText(contract.title)).toBeVisible();
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

    await mockPlaywrightCrud<ContractDefinition, DTOContractDefinition>({
      data: store.list,
      routeUrl: contractDefinitionApiUrl,
      page,
      searchResult: filterResult,
      forceFiltersMode: false,
      optionsResult: CONTRACT_DEFINITION_OPTIONS_REQUEST_RESULT,
    });
    await page.getByRole("button", { name: "Language: French" }).click();
    await page.getByRole("button", { name: "Clear" }).click();

    await Promise.all(
      store.list.map(async (contract) => {
        await expect(page.getByText(contract.title)).toBeVisible();
      }),
    );
    await page.getByRole("button", { name: "Filters" }).click();
    await expect(selectLangLocator).toBeVisible();
    await expect(page.locator(`[name='language']`)).toHaveValue("");
  });
});
