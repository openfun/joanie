import { expect, test } from "@playwright/test";
import { getBatchOrdersScenarioStore } from "@/tests/batch-orders/BatchOrderTestScenario";
import {
  getUrlCatchIdRegex,
  getUrlCatchSearchParamsRegex,
  mockPlaywrightCrud,
} from "@/tests/useResourceHandler";
import {
  BatchOrderListItem,
  transformBatchOrdersToListItems,
} from "@/services/api/models/BatchOrder";
import { PATH_ADMIN } from "@/utils/routes/path";
import { getBatchOrderListItemsScenarioStore } from "@/tests/batch-orders/BatchOrderListItemTestScenario";
import {
  DTOOrganization,
  Organization,
} from "@/services/api/models/Organization";
import { ORGANIZATION_OPTIONS_REQUEST_RESULT } from "@/tests/mocks/organizations/organization-mock";
import { formatShortDateTest } from "@/tests/utils";

const url = "http://localhost:8071/api/v1.0/admin/batch-orders/";
const catchIdRegex = getUrlCatchIdRegex(url);
const queryParamsRegex = getUrlCatchSearchParamsRegex(url);

test.describe("Batch Order view", () => {
  let store = getBatchOrdersScenarioStore();
  test.beforeEach(async ({ page }) => {
    store = getBatchOrdersScenarioStore();
    const list = transformBatchOrdersToListItems(store.list);

    await page.unroute(catchIdRegex);
    await page.route(catchIdRegex, async (route, request) => {
      const methods = request.method();
      if (methods === "GET") {
        const id = request.url().match(catchIdRegex)?.[1];
        await route.fulfill({ json: store.list.find((o) => o.id === id) });
      }
    });

    await page.unroute(queryParamsRegex);
    await page.route(queryParamsRegex, async (route, request) => {
      const methods = request.method();
      if (methods === "GET") {
        await route.fulfill({ json: list });
      }
    });

    await mockPlaywrightCrud<Organization, DTOOrganization>({
      data: store.organizations,
      routeUrl: "http://localhost:8071/api/v1.0/admin/organizations/",
      page,
      optionsResult: ORGANIZATION_OPTIONS_REQUEST_RESULT,
    });
  });

  test("Check all fields have the good value", async ({ page }) => {
    const batchOrder = store.list[0];
    batchOrder.created_on = new Date(
      Date.UTC(2024, 0, 23, 19, 30),
    ).toLocaleString("en-US");
    batchOrder.updated_on = new Date(
      Date.UTC(2024, 0, 23, 20, 30),
    ).toLocaleString("en-US");
    await page.goto(PATH_ADMIN.batch_orders.list);
    await page.getByRole("heading", { name: "Batch Orders" }).click();
    await page
      .getByRole("link", { name: batchOrder.offering.product.title })
      .click();

    await page
      .getByRole("heading", { name: "Batch Order informations" })
      .click();
    await expect(page.getByLabel("Organization", { exact: true })).toHaveValue(
      batchOrder.organization?.title ?? "",
    );
    await expect(page.getByLabel("Product")).toHaveValue(
      batchOrder.offering.product.title,
    );
    await expect(page.getByLabel("Course")).toHaveValue(
      batchOrder.offering.course.title,
    );
    await expect(page.getByLabel("Owner")).toHaveValue(
      batchOrder.owner.full_name ?? batchOrder.owner.username,
    );
    await expect(page.getByLabel("Company name")).toHaveValue(
      batchOrder.company_name,
    );
    await expect(page.getByLabel("Number of seats")).toHaveValue(
      batchOrder.nb_seats.toString(),
    );
    await expect(page.getByLabel("Total")).toHaveValue(batchOrder.total + "");
  });

  test("Check when organization is undefined", async ({ page }) => {
    const batchOrder = store.list[0];
    batchOrder.organization = null;
    await page.unroute(catchIdRegex);
    await page.route(catchIdRegex, async (route, request) => {
      const methods = request.method();
      if (methods === "GET") {
        await route.fulfill({ json: store.list[0] });
      }
    });
    await page.goto(PATH_ADMIN.batch_orders.list);
    await page.getByRole("heading", { name: "Batch Orders" }).click();
    await page
      .getByRole("link", { name: batchOrder.offering.product.title })
      .click();

    await page
      .getByRole("heading", { name: "Batch Order informations" })
      .click();
    await expect(page.getByLabel("Organization", { exact: true })).toHaveValue(
      "",
    );
    await expect(
      page
        .locator("div")
        .filter({ hasText: /^Organization$/ })
        .getByLabel("Click to view"),
    ).not.toBeVisible();
  });

  test("Check all field are in this view", async ({ page }) => {
    const batchOrder = store.list[0];
    await page.goto(PATH_ADMIN.batch_orders.list);
    await page.getByRole("heading", { name: "Batch Orders" }).click();
    await page
      .getByRole("link", { name: batchOrder.offering.product.title })
      .click();
    await page.getByRole("heading", { name: "Batch Orders" }).click();
    await page
      .getByRole("heading", { name: "Batch Order informations" })
      .click();
    await expect(
      page
        .getByRole("alert")
        .first()
        .getByText(
          "In this view, you can see the details of a batch order, such as the company, seats, and status.",
        ),
    ).toBeVisible();
    await expect(
      page.getByLabel("Organization", { exact: true }),
    ).toBeVisible();
    await expect(page.getByLabel("Product")).toBeVisible();
    await expect(page.getByLabel("Course")).toBeVisible();
    await expect(page.getByLabel("Owner")).toBeVisible();
    await expect(page.getByLabel("Company name")).toBeVisible();
    await expect(page.getByLabel("Number of seats")).toBeVisible();
    await expect(page.getByRole("textbox", { name: "State" })).toBeVisible();
    await expect(page.getByLabel("Total")).toBeVisible();
  });
});

test.describe("Batch Order list", () => {
  let store = getBatchOrderListItemsScenarioStore();
  test.beforeEach(async ({ page }) => {
    store = getBatchOrderListItemsScenarioStore();

    await mockPlaywrightCrud<BatchOrderListItem, any>({
      data: store.list,
      routeUrl: "http://localhost:8071/api/v1.0/admin/batch-orders/",
      page,
      searchResult: store.list[1],
    });
  });

  test("Check all the column are presents", async ({ page }) => {
    await page.goto(PATH_ADMIN.batch_orders.list);
    await expect(
      page.getByRole("heading", { name: "Batch Orders" }),
    ).toBeVisible();

    await expect(
      page.getByRole("columnheader", { name: "Product" }),
    ).toBeVisible();
    await expect(
      page.getByRole("columnheader", { name: "Company" }),
    ).toBeVisible();
    await expect(
      page.getByRole("columnheader", { name: "Owner" }),
    ).toBeVisible();
    await expect(
      page.getByRole("columnheader", { name: "Organization" }),
    ).toBeVisible();
    await expect(
      page.getByRole("columnheader", { name: "Seats" }),
    ).toBeVisible();
    await expect(
      page.getByRole("columnheader", { name: "State" }),
    ).toBeVisible();
    await expect(
      page.getByRole("columnheader", { name: "Created on" }),
    ).toBeVisible();
    await expect(
      page.getByRole("columnheader", { name: "Updated on" }),
    ).toBeVisible();
    await expect(
      page.getByRole("columnheader", { name: "Total" }),
    ).toBeVisible();
  });

  test("Check all the batch orders are presents", async ({ page }) => {
    await page.goto(PATH_ADMIN.batch_orders.list);
    await expect(
      page.getByRole("heading", { name: "Batch Orders" }),
    ).toBeVisible();
    await Promise.all(
      store.list.map(async (batchOrder) => {
        const rowLocator = page.locator(`[data-id='${batchOrder.id}']`);
        await expect(rowLocator).toBeVisible();
        await expect(
          rowLocator.getByRole("gridcell", { name: batchOrder.product_title }),
        ).toBeVisible();
        await expect(
          rowLocator.getByRole("gridcell", { name: batchOrder.company_name }),
        ).toBeVisible();
        await expect(
          rowLocator.getByRole("gridcell", { name: batchOrder.owner_name }),
        ).toBeVisible();
        await expect(
          rowLocator.getByRole("gridcell", {
            name: batchOrder.organization_title,
          }),
        ).toBeVisible();
        await expect(
          rowLocator.getByRole("gridcell", {
            name: batchOrder.nb_seats.toString(),
            exact: true,
          }),
        ).toBeVisible();
        await expect(
          rowLocator.getByRole("gridcell", { name: batchOrder.state }),
        ).toBeVisible();
        await expect(
          rowLocator.getByRole("gridcell", {
            name: await formatShortDateTest(page, batchOrder.created_on),
          }),
        ).toBeVisible();
        await expect(
          rowLocator.getByRole("gridcell", {
            name: await formatShortDateTest(page, batchOrder.updated_on),
          }),
        ).toBeVisible();
      }),
    );
  });

  test("Check ordering", async ({ page }) => {
    await page.goto(PATH_ADMIN.batch_orders.list);

    const header = page.getByRole("columnheader", { name: "Company" });
    const field = await header.getAttribute("data-field");
    await header.click();

    let titles = await page
      .locator(`[role='gridcell'][data-field='${field}']`)
      .allInnerTexts();
    expect(titles).not.toHaveLength(0);
    expect(titles).toEqual(titles.toSorted());

    await header.click();
    await page.waitForLoadState("networkidle");

    titles = await page
      .locator(`[role='gridcell'][data-field='${field}']`)
      .allInnerTexts();
    expect(titles).not.toHaveLength(0);
    expect(titles).toEqual(titles.toSorted().reverse());
  });
});
