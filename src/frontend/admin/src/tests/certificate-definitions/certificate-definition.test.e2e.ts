import { expect, test } from "@playwright/test";
import { getCertificateDefinitionScenarioStore } from "@/tests/certificate-definitions/CertificateDefinitionTestScenario";
import {
  getUrlCatchSearchParamsRegex,
  mockPlaywrightCrud,
} from "@/tests/useResourceHandler";
import {
  CertificateDefinition,
  DTOCertificateDefinition,
} from "@/services/api/models/CertificateDefinition";
import { PATH_ADMIN } from "@/utils/routes/path";
import { expectHaveClasses } from "@/tests/utils";

const certificateDefinitionApiUrl =
  "http://localhost:8071/api/v1.0/admin/certificate-definitions/";

const searchPlaceholder = "Search by title or name";

test.describe("Certificate definition form", () => {
  let store = getCertificateDefinitionScenarioStore();

  test.beforeEach(async ({ page }) => {
    store = getCertificateDefinitionScenarioStore();
    await mockPlaywrightCrud<CertificateDefinition, DTOCertificateDefinition>({
      data: store.list,
      routeUrl: certificateDefinitionApiUrl,
      page,
      createCallback: store.postUpdate,
      updateCallback: store.postUpdate,
      searchResult: store.list[1],
    });
  });

  test("Create a new certificate definition", async ({ page }) => {
    store = getCertificateDefinitionScenarioStore(5);
    await mockPlaywrightCrud<CertificateDefinition, DTOCertificateDefinition>({
      data: store.list,
      routeUrl: certificateDefinitionApiUrl,
      page,
      createCallback: store.postUpdate,
      updateCallback: store.postUpdate,
      searchResult: store.list[1],
    });
    await page.goto(PATH_ADMIN.certificates.list);
    await page
      .getByRole("heading", { name: "Certificates definitions" })
      .click();

    // Go to the form
    await page.getByRole("button", { name: "Add" }).click();
    await expect(
      page.getByRole("heading", { name: "Add certificate definition" }),
    ).toBeVisible();

    // Fill the form and submit
    await page.getByLabel("Title").click();
    await page.getByLabel("Title").fill("Test title");
    await page.getByLabel("Name").click();
    await page.getByLabel("Name").fill("Test name");
    await page.getByLabel("Description").click();
    await page.getByLabel("Description").fill("Test description");
    await page.getByRole("button", { name: "Submit" }).click();

    // Get the successfully notification
    await expect(
      page.getByText("Operation completed successfully."),
    ).toBeVisible();

    // Go to the list, and check that the new certificate definition is present in the list
    await page.getByRole("link", { name: "List" }).click();
    await page.getByRole("link", { name: "Test title", exact: true }).click();
  });

  test("Add a certificate with a name already in use.", async ({ page }) => {
    const certificateDefinition = store.list[0];
    await page.goto(PATH_ADMIN.certificates.list);
    await expect(
      page.getByRole("heading", { name: "Certificates definitions" }),
    ).toBeVisible();

    // Go to the form
    await page.getByRole("button", { name: "Add" }).click();
    await expect(
      page.getByRole("heading", { name: "Add certificate definition" }),
    ).toBeVisible();

    // Fill the form and submit
    await page.getByLabel("Title").click();
    await page.getByLabel("Title").fill(certificateDefinition.title);
    await page.getByLabel("Name").click();
    await page.getByLabel("Name").fill(certificateDefinition.name);
    await page.getByLabel("Description").click();
    await page
      .getByLabel("Description")
      .fill(certificateDefinition.description ?? "");

    const urlRegex = getUrlCatchSearchParamsRegex(certificateDefinitionApiUrl);
    await page.unroute(urlRegex);
    await page.route(urlRegex, async (route, request) => {
      const methods = request.method();

      if (methods === "POST") {
        await route.fulfill({
          status: 400,
          json: {
            name: ["This definition certification name is already in use"],
          },
        });
      }
    });

    await page.getByRole("button", { name: "Submit" }).click();

    // Get the successfully notification
    await expect(
      page.getByText(
        "An error occurred while creating the certificate definition. Please retry later.",
      ),
    ).toBeVisible();

    await expectHaveClasses(
      page.getByText("This definition certification name is already in use"),
      "Mui-error",
    );
  });

  test("Edit a certificate definition", async ({ page }) => {
    await page.goto(PATH_ADMIN.certificates.list);
    const certificateDefinition = store.list[0];
    const oldTitle = certificateDefinition.title + "";
    const newTitle = certificateDefinition.title + " updated";

    await expect(
      page.getByRole("heading", { name: "Certificates definitions" }),
    ).toBeVisible();

    await page
      .getByRole("row", { name: certificateDefinition.name })
      .getByRole("button")
      .click();
    await page.getByRole("menuitem", { name: "Edit" }).click();
    await expect(
      page.getByRole("heading", {
        name: `Edit certificate: ${certificateDefinition.title}`,
      }),
    ).toBeVisible();

    await page.getByLabel("Title").click();
    await page.getByLabel("Title").fill(newTitle);

    await page.getByRole("button", { name: "Submit" }).click();
    // Get the successfully notification
    await expect(
      page.getByText("Operation completed successfully."),
    ).toBeVisible();
    await page.getByRole("link", { name: "List" }).click();
    await expect(
      page.getByRole("link", { name: oldTitle, exact: true }),
    ).toHaveCount(0);

    await expect(
      page.getByRole("link", { name: newTitle, exact: true }),
    ).toHaveCount(1);
  });

  test("Test sending an empty form, and check error messages", async ({
    page,
  }) => {
    await page.goto(PATH_ADMIN.certificates.list);
    await page.getByRole("button", { name: "Add" }).click();
    await page.getByRole("button", { name: "Submit" }).click();

    // Title and name are mandatory
    await expectHaveClasses(
      page.getByText("title is a required field"),
      "Mui-error",
    );
    await expectHaveClasses(
      page.getByText("name is a required field"),
      "Mui-error",
    );
  });

  test("Click on an item in the list and use it as a template from its form", async ({
    page,
  }) => {
    await page.goto(PATH_ADMIN.certificates.list);
    const certificateDefinition = store.list[0];
    await page.getByRole("link", { name: certificateDefinition.name }).click();
    await expect(
      page.getByRole("heading", {
        name: `Edit certificate: ${certificateDefinition.title}`,
      }),
    ).toBeVisible();
    await page.getByRole("link", { name: "Use as a template" }).click();
    await expect(
      page.getByRole("heading", { name: "Add certificate definition" }),
    ).toBeVisible();
    await expect(page.getByText("Certificates definitions")).toBeVisible();
    await expect(page.getByRole("link", { name: "List" })).toBeVisible();
    await expect(page.getByText("Create", { exact: true })).toBeVisible();
    await expect(page.getByLabel("Title")).toHaveValue(
      certificateDefinition.title,
    );
    await expect(page.getByLabel("Name")).toHaveValue(
      certificateDefinition.name,
    );
    await expect(page.getByLabel("Description")).toHaveValue(
      certificateDefinition.description ?? "",
    );
  });

  test("Use an object from the list as a template via its action menu", async ({
    page,
  }) => {
    await page.goto(PATH_ADMIN.certificates.list);
    const certificateDefinition = store.list[0];
    await page
      .getByRole("row", { name: certificateDefinition.name })
      .getByRole("button")
      .click();
    await page.getByRole("menuitem", { name: "Use as a template" }).click();
    await expect(
      page.getByRole("heading", { name: "Add certificate definition" }),
    ).toBeVisible();

    await expect(page.getByLabel("Title")).toHaveValue(
      certificateDefinition.title,
    );
    await expect(page.getByLabel("Name")).toHaveValue(
      certificateDefinition.name,
    );
    await expect(page.getByLabel("Description")).toHaveValue(
      certificateDefinition.description ?? "",
    );
  });
});

test.describe("Certificate definition list", () => {
  let store = getCertificateDefinitionScenarioStore();

  test.beforeEach(async ({ page }) => {
    store = getCertificateDefinitionScenarioStore();
    await mockPlaywrightCrud<CertificateDefinition, DTOCertificateDefinition>({
      data: store.list,
      routeUrl: certificateDefinitionApiUrl,
      page,
      createCallback: store.postUpdate,
      updateCallback: store.postUpdate,
      searchResult: store.list[1],
    });
  });

  test("Render the entire list and check that all elements are present", async ({
    page,
  }) => {
    await page.goto(PATH_ADMIN.certificates.list);
    await expect(page.getByPlaceholder(searchPlaceholder)).toBeVisible();

    // await expect(page.getByText(certificateDefinition.name)).toBeVisible();
    await Promise.all(
      store.list.map(async (certificateDefinition, index) => {
        if (index > 19) {
          return;
        }
        await expect(page.getByText(certificateDefinition.title)).toBeVisible();
        await expect(page.getByText(certificateDefinition.name)).toBeVisible();
      }),
    );
    await page.getByLabel("Go to next page").click();
    await Promise.all(
      store.list.map(async (certificateDefinition, index) => {
        if (index <= 19) {
          return;
        }
        await expect(page.getByText(certificateDefinition.title)).toBeVisible();
        await expect(page.getByText(certificateDefinition.name)).toBeVisible();
      }),
    );
  });

  test("Delete a certificate definition", async ({ page }) => {
    await page.goto(PATH_ADMIN.certificates.list);
    const toDelete = store.list[2];
    await expect(page.getByRole("row", { name: toDelete.title })).toHaveCount(
      1,
    );
    await page
      .getByRole("row", { name: toDelete.title })
      .getByRole("button")
      .click();
    await page.getByRole("menuitem", { name: "Delete" }).click();
    await page.getByRole("heading", { name: "Delete an entity" }).click();
    await page
      .getByText(
        `Are you sure you want to delete this entity (${toDelete.name}) ?`,
      )
      .click();
    await page.getByRole("button", { name: "Validate" }).click();
    await page.getByText("Operation completed successfully.").click();
    await expect(page.getByRole("row", { name: toDelete.title })).toHaveCount(
      0,
    );
  });

  test("Render the entire list and use search", async ({ page }) => {
    store = getCertificateDefinitionScenarioStore(5);
    await mockPlaywrightCrud<CertificateDefinition, DTOCertificateDefinition>({
      data: store.list,
      routeUrl: certificateDefinitionApiUrl,
      page,
      searchTimeout: 200,
      searchResult: store.list[1],
    });
    await page.goto(PATH_ADMIN.certificates.list);
    await expect(page.getByPlaceholder(searchPlaceholder)).toBeVisible();

    await Promise.all(
      store.list.map(async (certificateDefinition) => {
        await expect(page.getByText(certificateDefinition.title)).toBeVisible();
        await expect(page.getByText(certificateDefinition.name)).toBeVisible();
      }),
    );

    await page.getByPlaceholder(searchPlaceholder).click();
    await page.getByPlaceholder(searchPlaceholder).fill("search");
    await expect(page.getByTestId("circular-loader-container")).toBeVisible();
    await expect(page.getByTestId("circular-loader-container")).toBeHidden();

    await Promise.all(
      store.list.map(async (certificateDefinition, index) => {
        if (index === 1) {
          await expect(
            page.getByText(certificateDefinition.title),
          ).toBeVisible();
          await expect(
            page.getByText(certificateDefinition.name),
          ).toBeVisible();
        } else {
          await expect(
            page.getByText(certificateDefinition.title),
          ).toBeHidden();
          await expect(page.getByText(certificateDefinition.name)).toBeHidden();
        }
      }),
    );

    await page.getByPlaceholder(searchPlaceholder).click();
    await page.getByPlaceholder(searchPlaceholder).fill("");
    await Promise.all(
      store.list.map(async (certificateDefinition) => {
        await expect(page.getByText(certificateDefinition.title)).toBeVisible();
        await expect(page.getByText(certificateDefinition.name)).toBeVisible();
      }),
    );
  });
});
