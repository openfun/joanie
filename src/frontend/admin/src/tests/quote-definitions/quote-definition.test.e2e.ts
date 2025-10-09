import { expect, test } from "@playwright/test";
import { mockPlaywrightCrud } from "@/tests/useResourceHandler";
import { getQuoteDefinitionScenarioStore } from "@/tests/quote-definitions/QuoteDefinitionTestScenario";
import {
  QuoteDefinition,
  DTOQuoteDefinition,
} from "@/services/api/models/QuoteDefinition";
import { PATH_ADMIN } from "@/utils/routes/path";
import { expectHaveClasses } from "@/tests/utils";
import { QUOTE_DEFINITION_OPTIONS_REQUEST_RESULT } from "@/tests/mocks/quote-definitions/quote-definition-mocks";

const quoteDefinitionApiUrl =
  "http://localhost:8071/api/v1.0/admin/quote-definitions/";

test.describe("Quote definition form", () => {
  let store = getQuoteDefinitionScenarioStore();

  test.beforeEach(async ({ page }) => {
    store = getQuoteDefinitionScenarioStore();
    await mockPlaywrightCrud<QuoteDefinition, DTOQuoteDefinition>({
      data: store.list,
      routeUrl: quoteDefinitionApiUrl,
      optionsResult: QUOTE_DEFINITION_OPTIONS_REQUEST_RESULT,
      page,
      createCallback: store.postUpdate,
      updateCallback: store.postUpdate,
      searchResult: store.list[1],
    });
  });

  test("Navigate to quote definitions list through navigation menu", async ({
    page,
  }) => {
    await page.goto(PATH_ADMIN.rootAdmin);
    await expect(
      page.getByRole("button", { name: "Quote definitions" }),
    ).toBeVisible();
    await page.getByRole("button", { name: "Quote definitions" }).click();
    await expect(page).toHaveURL(PATH_ADMIN.quote_definition.list);
    await expect(
      page.getByRole("heading", { name: "Quote definitions" }),
    ).toBeVisible();
  });

  test("Check that the form is complete and contains the necessary", async ({
    page,
  }) => {
    await page.goto(PATH_ADMIN.quote_definition.list);
    await page.getByRole("button", { name: "Add" }).click();
    await expect(
      page.getByRole("heading", { name: "Add quote definition" }),
    ).toBeVisible();

    await expect(
      page.getByRole("heading", { name: "Main information's" }),
    ).toBeVisible();

    await expect(page.getByTestId("simpleCard").getByRole("alert")).toHaveCount(
      1,
    );

    await expect(
      page.getByText(
        "This is a quote template that will be used to issue quotes.",
      ),
    ).toHaveCount(1);

    await expect(page.getByTestId("InfoOutlinedIcon")).toHaveCount(1);
    await expect(page.getByLabel("Title", { exact: true })).toHaveCount(1);
    await page.getByTestId("quote-definition-language-input").click();
    await expect(page.getByRole("option", { name: "English" })).toHaveCount(1);
    await expect(page.getByRole("option", { name: "French" })).toHaveCount(1);
    await page.getByRole("option", { name: "French" }).click();
    await page.getByTestId("quote-definition-template-name-input").click();
    await expect(
      page.getByRole("option", { name: "Quote Default" }),
    ).toHaveCount(1);
    await page.getByRole("option", { name: "Quote Default" }).click();
    await expect(page.getByLabel("Description")).toHaveCount(1);
    await expect(page.getByRole("heading", { name: "Body" })).toBeVisible();
    await expect(
      page.getByTestId("md-editor-body").getByRole("textbox"),
    ).toHaveCount(1);
  });

  test("Create a new quote definition ", async ({ page }) => {
    await page.goto(PATH_ADMIN.quote_definition.list);
    await page.getByRole("button", { name: "Add" }).click();
    await page.getByLabel("Title", { exact: true }).click();
    await page.getByLabel("Title", { exact: true }).fill("Quote title");
    await page.getByLabel("Language").click();
    await page.getByRole("option", { name: "English" }).click();
    await page.getByLabel("Template name").click();
    await page.getByRole("option", { name: "Quote Default" }).click();
    await page.getByLabel("Description").click();
    await page.getByLabel("Description").fill("Quote description");
    const MdEditorBody = page
      .getByTestId("md-editor-body")
      .getByRole("textbox");
    await MdEditorBody.click();
    await MdEditorBody.fill("### Body\n\n> Info");
    await page.getByRole("button", { name: "Submit" }).click();

    await expect(
      page.getByText("Operation completed successfully."),
    ).toBeVisible();

    await page.getByRole("link", { name: "List" }).click();
    await expect(
      page.getByRole("link", { name: "Quote title", exact: true }),
    ).toHaveCount(1);
    await expect(
      page.getByRole("row", { name: "Quote title en-us" }).getByTitle("en-us"),
    ).toHaveCount(1);
  });

  test("Validate an empty form and check error messages", async ({ page }) => {
    await page.goto(PATH_ADMIN.quote_definition.list);
    await page.getByRole("button", { name: "Add" }).click();
    await page.getByRole("button", { name: "Submit" }).click();

    await expectHaveClasses(
      page.getByText("title is a required field"),
      "Mui-error",
    );
    await expectHaveClasses(
      page.getByText("description is a required field"),
      "Mui-error",
    );
    await expectHaveClasses(
      page.getByText("name is a required field"),
      "Mui-error",
    );
    await expectHaveClasses(
      page.getByText("body is a required field"),
      "Mui-error",
    );
  });

  test("Edit quote definition", async ({ page }) => {
    const quoteDefinitionToUpdate = store.list[0];
    const oldTitle = quoteDefinitionToUpdate.title + "";
    const newTitle = quoteDefinitionToUpdate.title + " updated";
    await page.goto(PATH_ADMIN.quote_definition.list);
    await page
      .getByRole("link", {
        name: oldTitle,
        exact: true,
      })
      .click();

    await expect(
      page.getByRole("heading", {
        name: `Edit quote definition: ${quoteDefinitionToUpdate.title}`,
      }),
    ).toBeVisible();
    await page.getByLabel("Title", { exact: true }).click();
    await page.getByLabel("Title", { exact: true }).fill(newTitle);
    await page.getByLabel("Language").click();
    await page.getByRole("option", { name: "English" }).click();
    await expect(
      page.getByText("Operation completed successfully."),
    ).toBeVisible();

    await page.getByRole("link", { name: "List" }).click();

    await expect(
      page.getByRole("link", {
        name: oldTitle,
        exact: true,
      }),
    ).toHaveCount(0);
    await expect(
      page.getByRole("row", { name: `${newTitle} en-us` }),
    ).toHaveCount(1);
  });

  test("Click on a quote definition in the list and use it as a template from its form", async ({
    page,
  }) => {
    await page.goto(PATH_ADMIN.quote_definition.list);
    const quoteDefinition = store.list[0];
    await page.getByRole("link", { name: quoteDefinition.title }).click();

    await expect(
      page.getByRole("heading", {
        name: `Edit quote definition: ${quoteDefinition.title}`,
      }),
    ).toBeVisible();
    await page.getByRole("link", { name: "Use as a template" }).click();
    await expect(page.getByLabel("Title", { exact: true })).toHaveValue(
      quoteDefinition.title,
    );
    await expect(page.locator(`[name='language']`)).toHaveValue(
      quoteDefinition.language,
    );
    await expect(page.getByLabel("Description", { exact: true })).toHaveValue(
      quoteDefinition.description,
    );
    await expect(page.locator("[name='name']")).toHaveValue(
      quoteDefinition.name,
    );

    await expect(
      page.getByTestId("md-editor-body").getByRole("textbox"),
    ).toHaveValue(quoteDefinition.body ?? "");
  });

  test("Use a quote definition from the list as a template via its action menu", async ({
    page,
  }) => {
    await page.goto(PATH_ADMIN.quote_definition.list);
    const quoteDefinition = store.list[2];
    await page
      .getByRole("row", { name: `${quoteDefinition.title} fr-fr` })
      .getByRole("button")
      .click();
    await page.getByRole("menuitem", { name: "Use as a template" }).click();

    await expect(
      page.getByRole("heading", {
        name: `Add quote definition`,
      }),
    ).toBeVisible();

    await expect(page.getByLabel("Title", { exact: true })).toHaveValue(
      quoteDefinition.title,
    );
    await expect(page.locator(`[name='language']`)).toHaveValue(
      quoteDefinition.language,
    );
    await expect(page.getByLabel("Description", { exact: true })).toHaveValue(
      quoteDefinition.description ?? "",
    );

    await expect(
      page.getByTestId("md-editor-body").getByRole("textbox"),
    ).toHaveValue(quoteDefinition.body!);
  });
});
