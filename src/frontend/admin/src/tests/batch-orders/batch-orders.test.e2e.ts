import { expect, test } from "@playwright/test";
import { mockPlaywrightCrud } from "@/tests/useResourceHandler";
import { BatchOrderListItem } from "@/services/api/models/BatchOrder";
import { PATH_ADMIN } from "@/utils/routes/path";
import { getBatchOrderListItemsScenarioStore } from "@/tests/batch-orders/BatchOrderListItemTestScenario";
import { formatShortDateTest } from "@/tests/utils";

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
