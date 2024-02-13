import { expect, test } from "@playwright/test";
import { mockPlaywrightCrud } from "@/tests/useResourceHandler";
import { PATH_ADMIN } from "@/utils/routes/path";
import { getCertificateDefinitionScenarioStore } from "@/tests/certificate-definitions/CertificateDefinitionTestScenario";
import {
  CertificateDefinition,
  DTOCertificateDefinition,
} from "@/services/api/models/CertificateDefinition";
import { CERTIFICATE_DEFINITION_OPTIONS_REQUEST_RESULT } from "@/tests/mocks/certificate-definitions/certificate-definition-mocks";

const certificateDefinitionApiUrl =
  "http://localhost:8071/api/v1.0/admin/certificate-definitions/";
test.describe("Certificate definition filters", () => {
  let store = getCertificateDefinitionScenarioStore(5);

  test.beforeEach(async ({ page }) => {
    store = getCertificateDefinitionScenarioStore(5);
    await mockPlaywrightCrud<CertificateDefinition, DTOCertificateDefinition>({
      data: store.list,
      routeUrl: certificateDefinitionApiUrl,
      page,
      searchResult: store.list[1],
      optionsResult: CERTIFICATE_DEFINITION_OPTIONS_REQUEST_RESULT,
    });
  });

  test("Test that filters apply", async ({ page }) => {
    await page.goto(PATH_ADMIN.certificates.list);
    await expect(
      page.getByRole("heading", { name: "Certificates definitions" }),
    ).toBeVisible();

    // Check all certificate definition
    await Promise.all(
      store.list.map(async (certificate) => {
        await expect(
          page.getByRole("link", { name: certificate.title }),
        ).toBeVisible();
      }),
    );

    // Check if all filters are presents
    await expect(
      page.getByPlaceholder("Search by title or name"),
    ).toBeVisible();
    await page.getByRole("button", { name: "Filters" }).click();
    await expect(page.getByRole("heading", { name: "filters" })).toBeVisible();
    const selectTemplateLocator = page.getByLabel("Template");
    const templateInputLocator = page.locator(`[name='template']`);
    await expect(selectTemplateLocator).toBeVisible();
    await expect(templateInputLocator).toHaveValue("");

    // Select template
    await selectTemplateLocator.click();
    await expect(
      page.getByRole("option", { name: "Certificate" }),
    ).toBeVisible();
    await expect(page.getByRole("option", { name: "Degree" })).toBeVisible();

    // Check filters result
    const filterResult = [store.list[1], store.list[2]];
    await mockPlaywrightCrud<CertificateDefinition, DTOCertificateDefinition>({
      data: store.list,
      routeUrl: certificateDefinitionApiUrl,
      page,
      forceFiltersMode: true,
      searchResult: filterResult,
    });

    await page.getByRole("option", { name: "Certificate" }).click();
    await expect(templateInputLocator).toHaveValue("certificate");

    await page.getByLabel("close").click();
    await expect(
      page.getByRole("button", { name: "Template: certificate" }),
    ).toBeVisible();

    await Promise.all(
      filterResult.map(async (certificate) => {
        await expect(
          page.getByRole("link", { name: certificate.title }),
        ).toBeVisible();
      }),
    );

    // Remove all filters
    await page.getByRole("button", { name: "Clear" }).click();

    // Check that the list returns to the initial state
    await mockPlaywrightCrud<CertificateDefinition, DTOCertificateDefinition>({
      data: store.list,
      routeUrl: certificateDefinitionApiUrl,
      page,
      forceFiltersMode: false,
      searchResult: filterResult,
    });

    await Promise.all(
      store.list.map(async (certificate) => {
        await expect(
          page.getByRole("link", { name: certificate.title }),
        ).toBeVisible();
      }),
    );

    await page.getByRole("button", { name: "Filters" }).click();
    await expect(templateInputLocator).toHaveValue("");
    await expect(page.getByLabel("Template")).toBeVisible();
  });
});
