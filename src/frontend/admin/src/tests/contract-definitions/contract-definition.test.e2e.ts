import { expect, test } from "@playwright/test";
import { mockPlaywrightCrud } from "@/tests/useResourceHandler";
import { getContractDefinitionScenarioStore } from "@/tests/contract-definitions/ContractDefinitionTestScenario";
import {
  ContractDefinition,
  DTOContractDefinition,
} from "@/services/api/models/ContractDefinition";
import { PATH_ADMIN } from "@/utils/routes/path";
import { expectHaveClasses } from "@/tests/utils";
import { CONTRACT_DEFINITION_OPTIONS_REQUEST_RESULT } from "@/tests/mocks/contract-definitions/contract-definition-mocks";

const contractDefinitionApiUrl =
  "http://localhost:8071/api/v1.0/admin/contract-definitions/";

test.describe("Contract definition form", () => {
  let store = getContractDefinitionScenarioStore();

  test.beforeEach(async ({ page }) => {
    store = getContractDefinitionScenarioStore();
    await mockPlaywrightCrud<ContractDefinition, DTOContractDefinition>({
      data: store.list,
      routeUrl: contractDefinitionApiUrl,
      optionsResult: CONTRACT_DEFINITION_OPTIONS_REQUEST_RESULT,
      page,
      createCallback: store.postUpdate,
      updateCallback: store.postUpdate,
      searchResult: store.list[1],
    });
  });

  test("Check that the form is complete and contains the necessary", async ({
    page,
  }) => {
    await page.goto(PATH_ADMIN.contract_definition.list);
    await page.getByRole("button", { name: "Add" }).click();
    await expect(
      page.getByRole("heading", { name: "Add contract definition" }),
    ).toBeVisible();

    await expect(
      page.getByRole("heading", { name: "Main information's" }),
    ).toBeVisible();

    await expect(page.getByTestId("simpleCard").getByRole("alert")).toHaveCount(
      1,
    );

    await expect(
      page.getByText(
        "This is a contract template that will be used to issue contracts.",
      ),
    ).toHaveCount(1);

    await expect(page.getByTestId("InfoOutlinedIcon")).toHaveCount(1);
    await expect(page.getByLabel("Title", { exact: true })).toHaveCount(1);
    await page.getByTestId("contract-definition-language-input").click();
    await expect(page.getByRole("option", { name: "English" })).toHaveCount(1);
    await expect(page.getByRole("option", { name: "French" })).toHaveCount(1);
    await page.getByRole("option", { name: "French" }).click();
    await page.getByTestId("contract-definition-template-name-input").click();
    await expect(
      page.getByRole("option", { name: "Contract Definition Default" }),
    ).toHaveCount(1);
    await expect(
      page.getByRole("option", { name: "Contract Definition Unicamp" }),
    ).toHaveCount(1);
    await page
      .getByRole("option", { name: "Contract Definition Default" })
      .click();
    await expect(page.getByLabel("Description")).toHaveCount(1);
    await expect(page.getByRole("heading", { name: "Body" })).toBeVisible();
    await expect(
      page.getByTestId("md-editor-body").getByRole("textbox"),
    ).toHaveCount(1);
    await expect(page.getByRole("heading", { name: "Appendix" })).toBeVisible();
    await expect(
      page.getByTestId("md-editor-appendix").getByRole("textbox"),
    ).toHaveCount(1);
  });

  test("Create a new contract definition ", async ({ page }) => {
    await page.goto(PATH_ADMIN.contract_definition.list);
    await page.getByRole("button", { name: "Add" }).click();
    await page.getByLabel("Title", { exact: true }).click();
    await page.getByLabel("Title", { exact: true }).fill("Contract title");
    await page.getByLabel("Language").click();
    await page.getByRole("option", { name: "English" }).click();
    await page.getByLabel("Template name").click();
    await page
      .getByRole("option", { name: "Contract Definition Default" })
      .click();
    await page.getByLabel("Description").click();
    await page.getByLabel("Description").fill("Contract description");
    const MdEditorBody = page
      .getByTestId("md-editor-body")
      .getByRole("textbox");
    await MdEditorBody.click();
    await MdEditorBody.fill("### Body\n\n> Info");
    const MdEditorAppendix = page
      .getByTestId("md-editor-appendix")
      .getByRole("textbox");
    await MdEditorAppendix.click();
    await MdEditorAppendix.fill("### Appendix\n\n> Info");
    await page.getByRole("button", { name: "Submit" }).click();

    await expect(
      page.getByText("Operation completed successfully."),
    ).toBeVisible();

    await page.getByRole("link", { name: "List" }).click();
    await expect(
      page.getByRole("link", { name: "Contract title", exact: true }),
    ).toHaveCount(1);
    await expect(
      page
        .getByRole("row", { name: "Contract title en-us" })
        .getByTitle("en-us"),
    ).toHaveCount(1);
  });

  test("Validate an empty form and check error messages", async ({ page }) => {
    await page.goto(PATH_ADMIN.contract_definition.list);
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

  test("Edit contract definition", async ({ page }) => {
    const contractDefinitionToUpdate = store.list[0];
    const oldTitle = contractDefinitionToUpdate.title + "";
    const newTitle = contractDefinitionToUpdate.title + " updated";
    await page.goto(PATH_ADMIN.contract_definition.list);
    await page
      .getByRole("link", {
        name: oldTitle,
        exact: true,
      })
      .click();

    await expect(
      page.getByRole("heading", {
        name: `Edit contract definition: ${contractDefinitionToUpdate.title}`,
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

  test("Click on an contract definition in the list and use it as a template from its form", async ({
    page,
  }) => {
    await page.goto(PATH_ADMIN.contract_definition.list);
    const contractDefinition = store.list[0];
    await page.getByRole("link", { name: contractDefinition.title }).click();

    await expect(
      page.getByRole("heading", {
        name: `Edit contract definition: ${contractDefinition.title}`,
      }),
    ).toBeVisible();
    await page.getByRole("link", { name: "Use as a template" }).click();
    await expect(page.getByLabel("Title", { exact: true })).toHaveValue(
      contractDefinition.title,
    );
    await expect(page.locator(`[name='language']`)).toHaveValue(
      contractDefinition.language,
    );
    await expect(page.getByLabel("Description", { exact: true })).toHaveValue(
      contractDefinition.description,
    );
    await expect(page.locator("[name='name']")).toHaveValue(
      contractDefinition.name,
    );

    await expect(
      page.getByTestId("md-editor-body").getByRole("textbox"),
    ).toHaveValue(contractDefinition.body ?? "");

    await expect(
      page.getByTestId("md-editor-appendix").getByRole("textbox"),
    ).toHaveValue(contractDefinition.appendix ?? "");
  });

  test("Use an contract contract definition from the list as a template via its action menu", async ({
    page,
  }) => {
    await page.goto(PATH_ADMIN.contract_definition.list);
    const contractDefinition = store.list[2];
    await page
      .getByRole("row", { name: `${contractDefinition.title} fr-fr` })
      .getByRole("button")
      .click();
    await page.getByRole("menuitem", { name: "Use as a template" }).click();

    await expect(
      page.getByRole("heading", {
        name: `Add contract definition`,
      }),
    ).toBeVisible();

    await expect(page.getByLabel("Title", { exact: true })).toHaveValue(
      contractDefinition.title,
    );
    await expect(page.locator(`[name='language']`)).toHaveValue(
      contractDefinition.language,
    );
    await expect(page.getByLabel("Description", { exact: true })).toHaveValue(
      contractDefinition.description ?? "",
    );

    await expect(
      page.getByTestId("md-editor-body").getByRole("textbox"),
    ).toHaveValue(contractDefinition.body!);

    await expect(
      page.getByTestId("md-editor-appendix").getByRole("textbox"),
    ).toHaveValue(contractDefinition.appendix!);
  });
});
