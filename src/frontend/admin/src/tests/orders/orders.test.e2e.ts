import { expect, test } from "@playwright/test";
import { getOrdersScenarioStore } from "@/tests/orders/OrderTestScenario";
import {
  getUrlCatchIdRegex,
  getUrlCatchSearchParamsRegex,
  mockPlaywrightCrud,
} from "@/tests/useResourceHandler";
import {
  OrderInvoiceTypesEnum,
  OrderListItem,
  transformOrdersToOrderListItems,
} from "@/services/api/models/Order";
import { PATH_ADMIN } from "@/utils/routes/path";
import { getOrderListItemsScenarioStore } from "@/tests/orders/OrderListItemTestScenario";

test.describe("Order view", () => {
  let store = getOrdersScenarioStore();
  test.beforeEach(async ({ page }) => {
    const url = "http://localhost:8071/api/v1.0/admin/orders/";
    store = getOrdersScenarioStore();
    const list = transformOrdersToOrderListItems(store.list);
    const catchIdRegex = getUrlCatchIdRegex(url);
    await page.unroute(catchIdRegex);
    await page.route(catchIdRegex, async (route, request) => {
      const methods = request.method();
      if (methods === "GET") {
        await route.fulfill({ json: store.list[0] });
      }
    });

    const queryParamsRegex = getUrlCatchSearchParamsRegex(url);
    await page.unroute(queryParamsRegex);
    await page.route(queryParamsRegex, async (route, request) => {
      const methods = request.method();
      if (methods === "GET") {
        await route.fulfill({ json: list });
      }
    });
  });

  test("Check all field are the good value", async ({ page }) => {
    const order = store.list[0];
    await page.goto(PATH_ADMIN.orders.list);
    await page.getByRole("heading", { name: "Orders" }).click();
    await page.getByRole("link", { name: order.product.title }).click();

    await page.getByRole("heading", { name: "Order informations" }).click();
    await expect(page.getByLabel("Organization")).toHaveValue(
      order.organization.title,
    );
    await expect(page.getByLabel("Product")).toHaveValue(order.product.title);
    if (order.course) {
      await expect(page.getByLabel("Course")).toHaveValue(order.course.title);
    } else if (order.enrollment) {
      await expect(page.getByLabel("Course")).toHaveValue(order.enrollment.id);
    }
    await expect(page.getByLabel("Order group")).toHaveValue(
      order.order_group?.id ?? "-",
    );
    await expect(page.getByLabel("Owner")).toHaveValue(
      order.owner.full_name ?? order.owner.username,
    );

    await expect(page.getByLabel("Price")).toHaveValue(order.total + "");
    await page.getByRole("button", { name: "Invoice details" }).click();
    await expect(page.getByLabel("Type")).toHaveValue(
      order.main_invoice.type === OrderInvoiceTypesEnum.INVOICE
        ? "Invoice"
        : "Credit note",
    );
    await expect(page.getByLabel("Total")).toHaveValue(order.total + "");
    await expect(page.getByLabel("Billing address")).toHaveValue(
      order.main_invoice.recipient_address,
    );
    await expect(page.getByLabel("Created on")).toHaveValue(
      new Date(order.main_invoice.created_on).toLocaleDateString(),
    );
    await expect(page.getByLabel("Updated on")).toHaveValue(
      new Date(order.main_invoice.updated_on).toLocaleDateString(),
    );
    await expect(page.getByLabel("Balance")).toHaveValue(
      order.main_invoice.balance,
    );

    if (order.certificate) {
      await expect(page.getByLabel("Certificate")).toHaveValue(
        order.certificate.definition_title,
      );
    }
  });

  test("Check all field are in this view", async ({ page }) => {
    const order = store.list[0];
    await page.goto(PATH_ADMIN.orders.list);
    await page.getByRole("heading", { name: "Orders" }).click();
    await page.getByRole("link", { name: order.product.title }).click();
    await page.getByRole("heading", { name: "Orders" }).click();
    await page.getByRole("heading", { name: "Order informations" }).click();
    await expect(
      page
        .getByRole("alert")
        .first()
        .getByText(
          "In this view, you can see the details of an order, such as the user concerned, their status etc.",
        ),
    ).toBeVisible();
    await expect(page.getByLabel("Organization")).toBeVisible();
    await expect(page.getByLabel("Product")).toBeVisible();
    await expect(page.getByLabel("Course")).toBeVisible();
    await expect(page.getByLabel("Order group")).toBeVisible();
    await expect(page.getByLabel("Owner")).toBeVisible();
    await expect(page.getByRole("textbox", { name: "State" })).toBeVisible();
    await expect(page.getByLabel("Price")).toBeVisible();
    await expect(
      page.getByRole("button", { name: "Invoice details" }),
    ).toBeVisible();
    await page.getByRole("button", { name: "Invoice details" }).click();
    await expect(
      page
        .getByRole("alert")
        .nth(1)
        .getByText(
          "In this section, you have access to the main invoice with its total and balance, as well as sub-invoices (such as credit notes for example)",
        ),
    ).toBeVisible();
    await expect(
      page.getByLabel("Invoice details").getByLabel("State"),
    ).toBeVisible();
    await expect(page.getByLabel("Type")).toBeVisible();
    await expect(page.getByLabel("Total")).toBeVisible();
    await expect(page.getByLabel("Billing address")).toBeVisible();
    await expect(page.getByLabel("Created on")).toBeVisible();
    await expect(page.getByLabel("Updated on")).toBeVisible();
    await expect(page.getByLabel("Balance")).toBeVisible();
    if (order.certificate) {
      await expect(page.getByLabel("Certificate")).toBeVisible();
    }
  });
});

test.describe("Order list", () => {
  let store = getOrderListItemsScenarioStore();
  test.beforeEach(async ({ page }) => {
    store = getOrderListItemsScenarioStore();
    await mockPlaywrightCrud<OrderListItem, any>({
      data: store.list,
      routeUrl: "http://localhost:8071/api/v1.0/admin/orders/",
      page,
      searchResult: store.list[1],
    });
  });

  test("Check all the column are presents", async ({ page }) => {
    await page.goto(PATH_ADMIN.orders.list);
    await expect(page.getByRole("heading", { name: "Orders" })).toBeVisible();

    await expect(
      page.getByRole("columnheader", { name: "Organization" }),
    ).toBeVisible();
    await expect(
      page.getByRole("columnheader", { name: "Owner" }),
    ).toBeVisible();
    await expect(
      page.getByRole("columnheader", { name: "Product" }),
    ).toBeVisible();
    await expect(
      page.getByRole("columnheader", { name: "State" }),
    ).toBeVisible();
  });

  test("Check all the orders are presents", async ({ page }) => {
    await page.goto(PATH_ADMIN.orders.list);
    await expect(page.getByRole("heading", { name: "Orders" })).toBeVisible();
    await Promise.all(
      store.list.map(async (order) => {
        const rowLocator = page.locator(`[data-id='${order.id}']`);
        await expect(rowLocator).toBeVisible();
        await expect(
          rowLocator.getByRole("cell", { name: order.organization_title }),
        ).toBeVisible();
        await expect(
          rowLocator.getByRole("cell", { name: order.owner_name }),
        ).toBeVisible();
        await expect(
          rowLocator.getByRole("cell", { name: order.product_title }),
        ).toBeVisible();
        await expect(
          rowLocator.getByRole("cell", { name: order.state }),
        ).toBeVisible();
      }),
    );
  });
});
