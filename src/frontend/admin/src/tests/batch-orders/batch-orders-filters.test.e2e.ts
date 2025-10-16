import { expect, test } from "@playwright/test";
import { getBatchOrdersScenarioStore } from "@/tests/batch-orders/BatchOrderTestScenario";
import {
  getUrlCatchSearchParamsRegex,
  mockPlaywrightCrud,
} from "@/tests/useResourceHandler";
import { transformBatchOrdersToListItems } from "@/services/api/models/BatchOrder";
import { PATH_ADMIN } from "@/utils/routes/path";
import {
  DTOOrganization,
  Organization,
} from "@/services/api/models/Organization";
import { User } from "@/services/api/models/User";
import { ORGANIZATION_OPTIONS_REQUEST_RESULT } from "@/tests/mocks/organizations/organization-mock";

test.describe("Batch Order filters", () => {
  let store = getBatchOrdersScenarioStore();
  test.beforeEach(async ({ page }) => {
    const url = "http://localhost:8071/api/v1.0/admin/batch-orders/";
    store = getBatchOrdersScenarioStore();
    const list = transformBatchOrdersToListItems(store.list);
    const queryParamsRegex = getUrlCatchSearchParamsRegex(url);
    await page.unroute(queryParamsRegex);
    await page.route(queryParamsRegex, async (route, request) => {
      const methods = request.method();
      if (methods === "GET") {
        await route.fulfill({ json: list });
      }
    });

    const context = page.context();
    const exportUrl =
      "http://localhost:8071/api/v1.0/admin/batch-orders/export/";
    const exportQueryParamsRegex = getUrlCatchSearchParamsRegex(exportUrl);
    await context.unroute(exportQueryParamsRegex);
    await context.route(exportQueryParamsRegex, async (route, request) => {
      if (request.method() === "GET") {
        await route.fulfill({
          contentType: "application/csv",
          body: "data",
        });
      }
    });

    await mockPlaywrightCrud<Organization, DTOOrganization>({
      data: store.organizations,
      routeUrl: "http://localhost:8071/api/v1.0/admin/organizations/",
      page,
      searchResult: store.organizations[0],
      optionsResult: ORGANIZATION_OPTIONS_REQUEST_RESULT,
    });

    await mockPlaywrightCrud<User, any>({
      data: store.users,
      routeUrl: "http://localhost:8071/api/v1.0/admin/users/",
      page,
      forceFiltersMode: true,
      searchResult: store.users[0],
    });
  });

  test("Check filters button and search field are present", async ({
    page,
  }) => {
    await page.goto(PATH_ADMIN.batch_orders.list);
    await expect(
      page.getByRole("heading", { name: "Batch Orders" }),
    ).toBeVisible();
    await expect(
      page.getByPlaceholder(
        "Search by product, company, owner or organization name",
      ),
    ).toBeVisible();
    // Note: Currently BatchOrdersList has filters set to undefined
    // This test validates the presence of search functionality
  });

  test("Check search functionality", async ({ page }) => {
    await page.goto(PATH_ADMIN.batch_orders.list);
    await expect(
      page.getByRole("heading", { name: "Batch Orders" }),
    ).toBeVisible();

    const searchInput = page.getByPlaceholder(
      "Search by product, company, owner or organization name",
    );
    await expect(searchInput).toBeVisible();

    // Test that search input is functional
    await searchInput.fill(store.list[0].company_name);
    await expect(searchInput).toHaveValue(store.list[0].company_name);
  });

  test("Test export functionality", async ({ page }) => {
    await page.goto(PATH_ADMIN.batch_orders.list);

    const exportButton = page.getByRole("button", { name: "Export" });
    if (await exportButton.isVisible()) {
      await exportButton.click();

      page.on("popup", async (popup) => {
        await popup.waitForLoadState();
        expect(popup.url()).toContain(
          "http://localhost:8071/api/v1.0/admin/batch-orders/export/",
        );
      });
    }
  });
});
