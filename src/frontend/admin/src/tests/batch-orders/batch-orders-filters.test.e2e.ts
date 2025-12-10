import { expect, test } from "@playwright/test";
import { getBatchOrdersScenarioStore } from "@/tests/batch-orders/BatchOrderTestScenario";
import {
  getUrlCatchSearchParamsRegex,
  mockPlaywrightCrud,
} from "@/tests/useResourceHandler";
import {
  BatchOrderPaymentMethodEnum,
  BatchOrderStatesEnum,
  transformBatchOrdersToListItems,
} from "@/services/api/models/BatchOrder";
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

  test("Check all filter fields are present", async ({ page }) => {
    await page.goto(PATH_ADMIN.batch_orders.list);
    await expect(
      page.getByRole("heading", { name: "Batch Orders" }),
    ).toBeVisible();
    await expect(
      page.getByPlaceholder(
        "Search by product, company, owner or organization name",
      ),
    ).toBeVisible();
    await page.getByRole("button", { name: "Filters" }).click();
    await expect(
      page.getByTestId("select-batch-order-state-filter").getByLabel("State"),
    ).toBeVisible();
    await expect(
      page
        .getByTestId("select-batch-order-payment-method-filter")
        .getByLabel("Payment method"),
    ).toBeVisible();
    await expect(
      page.getByRole("combobox", { name: "Organization" }),
    ).toBeVisible();
    await expect(page.getByRole("combobox", { name: "Owner" })).toBeVisible();
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

  test("Check all filter chips", async ({ page }) => {
    await page.goto(PATH_ADMIN.batch_orders.list);
    await expect(
      page.getByRole("heading", { name: "Batch Orders" }),
    ).toBeVisible();
    await page.getByRole("button", { name: "Filters" }).click();

    // Select state filter
    await page
      .getByTestId("select-batch-order-state-filter")
      .getByLabel("State")
      .click();
    await page
      .getByRole("option", {
        name: BatchOrderStatesEnum.BATCH_ORDER_STATE_COMPLETED,
      })
      .click();

    // Select payment method filter
    await page
      .getByTestId("select-batch-order-payment-method-filter")
      .getByLabel("Payment method")
      .click();
    await page
      .getByRole("option", {
        name: BatchOrderPaymentMethodEnum.BATCH_ORDER_WITH_BANK_TRANSFER,
      })
      .click();

    // Select organization filter
    await page.getByRole("combobox", { name: "Organization" }).click();
    await page.getByRole("combobox", { name: "Organization" }).fill("o");
    await page
      .getByRole("option", { name: store.organizations[0].title })
      .click();

    // Select owner filter
    await page.getByRole("combobox", { name: "Owner" }).click();
    await page.getByRole("combobox", { name: "Owner" }).fill("u");
    await page.getByRole("option", { name: store.users[0].username }).click();

    await page.getByLabel("close").click();

    // Verify all filter chips are visible
    await expect(
      page.getByRole("button", {
        name: `State: ${BatchOrderStatesEnum.BATCH_ORDER_STATE_COMPLETED}`,
      }),
    ).toBeVisible();
    await expect(
      page.getByRole("button", {
        name: `Payment method: ${BatchOrderPaymentMethodEnum.BATCH_ORDER_WITH_BANK_TRANSFER}`,
      }),
    ).toBeVisible();
    await expect(
      page.getByRole("button", {
        name: `Organization: ${store.organizations[0].title}`,
      }),
    ).toBeVisible();
    await expect(
      page.getByRole("button", {
        name: `Owner: ${store.users[0].full_name} (${store.users[0].username})`,
      }),
    ).toBeVisible();
  });

  test("Test payment method filter functionality", async ({ page }) => {
    await page.goto(PATH_ADMIN.batch_orders.list);
    await expect(
      page.getByRole("heading", { name: "Batch Orders" }),
    ).toBeVisible();

    await page.getByRole("button", { name: "Filters" }).click();

    // Select payment method filter
    await page
      .getByTestId("select-batch-order-payment-method-filter")
      .getByLabel("Payment method")
      .click();
    await page
      .getByRole("option", {
        name: BatchOrderPaymentMethodEnum.BATCH_ORDER_WITH_PURCHASE_ORDER,
      })
      .click();

    await page.getByLabel("close").click();

    // Verify chip is visible
    await expect(
      page.getByRole("button", {
        name: `Payment method: ${BatchOrderPaymentMethodEnum.BATCH_ORDER_WITH_PURCHASE_ORDER}`,
      }),
    ).toBeVisible();

    // Clear filter
    await page
      .getByRole("button", {
        name: `Payment method: ${BatchOrderPaymentMethodEnum.BATCH_ORDER_WITH_PURCHASE_ORDER}`,
      })
      .getByTestId("CancelIcon")
      .click();

    // Verify chip is no longer visible
    await expect(
      page.getByRole("button", {
        name: `Payment method: ${BatchOrderPaymentMethodEnum.BATCH_ORDER_WITH_PURCHASE_ORDER}`,
      }),
    ).not.toBeVisible();
  });

  test("Test export functionality", async ({ page, context }) => {
    let exportRequestUrl = "";
    await context.route(/batch-orders\/export/, (route, request) => {
      exportRequestUrl = request.url();
      route.fulfill({ contentType: "text/csv", body: "data" });
    });

    await page.goto(PATH_ADMIN.batch_orders.list);

    const exportButton = page.getByRole("button", { name: "Export" });
    await expect(exportButton).toBeVisible();

    const pagePromise = context.waitForEvent("page");
    await exportButton.click();
    await pagePromise;

    expect(exportRequestUrl).toContain(
      "http://localhost:8071/api/v1.0/admin/batch-orders/export/",
    );
  });

  test("Test export with filters", async ({ page, context }) => {
    let exportRequestUrl = "";
    await context.route(/batch-orders\/export/, (route, request) => {
      exportRequestUrl = request.url();
      route.fulfill({ contentType: "text/csv", body: "data" });
    });

    await page.goto(PATH_ADMIN.batch_orders.list);

    await page.getByRole("button", { name: "Filters" }).click();
    await page
      .getByTestId("select-batch-order-state-filter")
      .getByLabel("State")
      .click();
    await page
      .getByRole("option", {
        name: BatchOrderStatesEnum.BATCH_ORDER_STATE_COMPLETED,
      })
      .click();
    await page.getByLabel("close").click();

    const pagePromise = context.waitForEvent("page");
    await page.getByRole("button", { name: "Export" }).click();
    await pagePromise;

    expect(exportRequestUrl).toContain(
      `state=${BatchOrderStatesEnum.BATCH_ORDER_STATE_COMPLETED}`,
    );
  });
});
