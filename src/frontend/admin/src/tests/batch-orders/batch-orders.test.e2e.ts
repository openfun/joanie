import { expect, test } from "@playwright/test";
import { getBatchOrdersScenarioStore } from "@/tests/batch-orders/BatchOrderTestScenario";
import {
  getUrlCatchIdRegex,
  getUrlCatchSearchParamsRegex,
  mockPlaywrightCrud,
} from "@/tests/useResourceHandler";
import {
  BatchOrderListItem,
  BatchOrderPaymentMethodEnum,
  BatchOrderStatesEnum,
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

  test("Cancel batch order", async ({ page }) => {
    const batchOrder = store.list[0];
    batchOrder.state = BatchOrderStatesEnum.BATCH_ORDER_STATE_DRAFT;

    await page.unroute(catchIdRegex);
    await page.route(catchIdRegex, async (route, request) => {
      const methods = request.method();
      if (methods === "GET") {
        await route.fulfill({ json: batchOrder });
      }

      if (methods === "DELETE") {
        batchOrder.state = BatchOrderStatesEnum.BATCH_ORDER_STATE_CANCELED;
        await route.fulfill({ json: batchOrder });
      }
    });
    await page.goto(PATH_ADMIN.batch_orders.list);
    await page.getByRole("heading", { name: "Batch Orders" }).click();
    await page
      .getByRole("link", { name: batchOrder.offering.product.title })
      .click();
    await expect(
      page.getByRole("heading", { name: "Batch order informations" }),
    ).toBeVisible();
    await expect(page.getByRole("textbox", { name: "State" })).toHaveValue(
      "draft",
    );

    // Check and click on the action button
    await expect(page.getByRole("button", { name: "Actions" })).toBeVisible();
    await page.getByRole("button", { name: "Actions" }).click();

    // Cancel order

    await expect(
      page.getByRole("menuitem", { name: "Cancel this batch order" }),
    ).toBeVisible();
    await page
      .getByRole("menuitem", { name: "Cancel this batch order" })
      .click();

    // Check after operation
    await expect(page.getByText("Operation completed")).toBeVisible();
    await expect(page.getByRole("textbox", { name: "State" })).toHaveValue(
      "canceled",
    );
  });

  test("Confirm quote for batch order", async ({ page }) => {
    const batchOrder = store.list[0];
    batchOrder.state = BatchOrderStatesEnum.BATCH_ORDER_STATE_QUOTED;
    batchOrder.total = null;

    const confirmQuoteRegex = new RegExp(
      `${url}${batchOrder.id}/confirm-quote/`,
    );

    await page.unroute(catchIdRegex);
    await page.route(catchIdRegex, async (route, request) => {
      const methods = request.method();
      if (methods === "GET") {
        await route.fulfill({ json: batchOrder });
      }
    });

    await page.unroute(confirmQuoteRegex);
    await page.route(confirmQuoteRegex, async (route, request) => {
      const methods = request.method();
      if (methods === "PATCH") {
        const postData = request.postDataJSON();
        batchOrder.total = postData.total;
        batchOrder.state = BatchOrderStatesEnum.BATCH_ORDER_STATE_TO_SIGN;
        await route.fulfill({ json: batchOrder });
      }
    });

    await page.goto(PATH_ADMIN.batch_orders.list);
    await page.getByRole("heading", { name: "Batch Orders" }).click();
    await page
      .getByRole("link", { name: batchOrder.offering.product.title })
      .click();
    await expect(
      page.getByRole("heading", { name: "Batch order informations" }),
    ).toBeVisible();
    await expect(page.getByRole("textbox", { name: "State" })).toHaveValue(
      "quoted",
    );

    // Check and click on the action button
    await expect(page.getByRole("button", { name: "Actions" })).toBeVisible();
    await page.getByRole("button", { name: "Actions" }).click();

    // Click confirm quote
    await expect(
      page.getByRole("menuitem", { name: "Confirm quote" }),
    ).toBeVisible();
    await page.getByRole("menuitem", { name: "Confirm quote" }).click();

    // Modal should be visible
    await expect(
      page.getByRole("dialog").getByRole("heading", { name: "Confirm Quote" }),
    ).toBeVisible();

    // Enter total amount
    const totalInput = page.getByTestId("confirm-quote-total-input");
    await expect(totalInput).toBeVisible();
    await totalInput.fill("123.45");

    // Click confirm button in modal
    await page
      .getByRole("dialog")
      .getByRole("button", { name: "Confirm" })
      .click();

    // Check after operation
    await expect(page.getByText("Batch order quote confirmed.")).toBeVisible();
    await expect(page.getByLabel("Total", { exact: true })).toHaveValue(
      "123.45",
    );
    await expect(page.getByRole("textbox", { name: "State" })).toHaveValue(
      "to_sign",
    );
  });

  test("Confirm quote button is disabled when state is not quoted", async ({
    page,
  }) => {
    const batchOrder = store.list[0];
    batchOrder.state = BatchOrderStatesEnum.BATCH_ORDER_STATE_DRAFT;

    await page.unroute(catchIdRegex);
    await page.route(catchIdRegex, async (route, request) => {
      const methods = request.method();
      if (methods === "GET") {
        await route.fulfill({ json: batchOrder });
      }
    });

    await page.goto(PATH_ADMIN.batch_orders.list);
    await page.getByRole("heading", { name: "Batch Orders" }).click();
    await page
      .getByRole("link", { name: batchOrder.offering.product.title })
      .click();
    await expect(
      page.getByRole("heading", { name: "Batch order informations" }),
    ).toBeVisible();

    // Check and click on the action button
    await expect(page.getByRole("button", { name: "Actions" })).toBeVisible();
    await page.getByRole("button", { name: "Actions" }).click();

    // Confirm quote should be disabled
    const confirmQuoteMenuItem = page.getByRole("menuitem", {
      name: "Confirm quote",
    });
    await expect(confirmQuoteMenuItem).toBeVisible();
    await expect(confirmQuoteMenuItem).toHaveAttribute("aria-disabled", "true");
  });

  test("Confirm purchase order for batch order", async ({ page }) => {
    const batchOrder = store.list[0];
    batchOrder.state = BatchOrderStatesEnum.BATCH_ORDER_STATE_QUOTED;
    batchOrder.payment_method =
      BatchOrderPaymentMethodEnum.BATCH_ORDER_WITH_PURCHASE_ORDER;
    batchOrder.total = 123.45;

    const confirmPurchaseOrderRegex = new RegExp(
      `${url}${batchOrder.id}/confirm-purchase-order/`,
    );

    await page.unroute(catchIdRegex);
    await page.route(catchIdRegex, async (route, request) => {
      const methods = request.method();
      if (methods === "GET") {
        await route.fulfill({ json: batchOrder });
      }
    });

    await page.unroute(confirmPurchaseOrderRegex);
    await page.route(confirmPurchaseOrderRegex, async (route, request) => {
      const methods = request.method();
      if (methods === "PATCH") {
        batchOrder.state = BatchOrderStatesEnum.BATCH_ORDER_STATE_TO_SIGN;
        await route.fulfill({ json: batchOrder });
      }
    });

    await page.goto(PATH_ADMIN.batch_orders.list);
    await page.getByRole("heading", { name: "Batch Orders" }).click();
    await page
      .getByRole("link", { name: batchOrder.offering.product.title })
      .click();
    await expect(
      page.getByRole("heading", { name: "Batch order informations" }),
    ).toBeVisible();
    await expect(page.getByRole("textbox", { name: "State" })).toHaveValue(
      "quoted",
    );

    // Check and click on the action button
    await expect(page.getByRole("button", { name: "Actions" })).toBeVisible();
    await page.getByRole("button", { name: "Actions" }).click();

    // Click confirm purchase order
    await expect(
      page.getByRole("menuitem", { name: "Confirm purchase order" }),
    ).toBeVisible();
    await page
      .getByRole("menuitem", { name: "Confirm purchase order" })
      .click();

    // Check after operation
    await expect(
      page.getByText("Batch order purchase order confirmed."),
    ).toBeVisible();
    await expect(page.getByRole("textbox", { name: "State" })).toHaveValue(
      "to_sign",
    );
  });

  test("Confirm purchase order button is disabled when conditions are not met", async ({
    page,
  }) => {
    const batchOrder = store.list[0];
    batchOrder.state = BatchOrderStatesEnum.BATCH_ORDER_STATE_QUOTED;
    batchOrder.payment_method =
      BatchOrderPaymentMethodEnum.BATCH_ORDER_WITH_BANK_TRANSFER;
    batchOrder.total = 123.45;

    await page.unroute(catchIdRegex);
    await page.route(catchIdRegex, async (route, request) => {
      const methods = request.method();
      if (methods === "GET") {
        await route.fulfill({ json: batchOrder });
      }
    });

    await page.goto(PATH_ADMIN.batch_orders.list);
    await page.getByRole("heading", { name: "Batch Orders" }).click();
    await page
      .getByRole("link", { name: batchOrder.offering.product.title })
      .click();
    await expect(
      page.getByRole("heading", { name: "Batch order informations" }),
    ).toBeVisible();

    // Check and click on the action button
    await expect(page.getByRole("button", { name: "Actions" })).toBeVisible();
    await page.getByRole("button", { name: "Actions" }).click();

    // Confirm purchase order should be disabled
    const confirmPurchaseOrderMenuItem = page.getByRole("menuitem", {
      name: "Confirm purchase order",
    });
    await expect(confirmPurchaseOrderMenuItem).toBeVisible();
    await expect(confirmPurchaseOrderMenuItem).toHaveAttribute(
      "aria-disabled",
      "true",
    );
  });

  test("Confirm bank transfer for batch order", async ({ page }) => {
    const batchOrder = store.list[0];
    batchOrder.state = BatchOrderStatesEnum.BATCH_ORDER_STATE_PENDING;
    batchOrder.payment_method =
      BatchOrderPaymentMethodEnum.BATCH_ORDER_WITH_BANK_TRANSFER;
    batchOrder.total = 123.45;

    const confirmBankTransferRegex = new RegExp(
      `${url}${batchOrder.id}/confirm-bank-transfer/`,
    );

    await page.unroute(catchIdRegex);
    await page.route(catchIdRegex, async (route, request) => {
      const methods = request.method();
      if (methods === "GET") {
        await route.fulfill({ json: batchOrder });
      }
    });

    await page.unroute(confirmBankTransferRegex);
    await page.route(confirmBankTransferRegex, async (route, request) => {
      const methods = request.method();
      if (methods === "POST") {
        batchOrder.state = BatchOrderStatesEnum.BATCH_ORDER_STATE_COMPLETED;
        await route.fulfill({ json: batchOrder });
      }
    });

    await page.goto(PATH_ADMIN.batch_orders.list);
    await page.getByRole("heading", { name: "Batch Orders" }).click();
    await page
      .getByRole("link", { name: batchOrder.offering.product.title })
      .click();
    await expect(
      page.getByRole("heading", { name: "Batch order informations" }),
    ).toBeVisible();
    await expect(page.getByRole("textbox", { name: "State" })).toHaveValue(
      "pending",
    );

    // Check and click on the action button
    await expect(page.getByRole("button", { name: "Actions" })).toBeVisible();
    await page.getByRole("button", { name: "Actions" }).click();

    // Click confirm bank transfer
    await expect(
      page.getByRole("menuitem", { name: "Confirm bank transfer" }),
    ).toBeVisible();
    await page.getByRole("menuitem", { name: "Confirm bank transfer" }).click();

    // Check after operation
    await expect(
      page.getByText("Batch order bank transfer confirmed."),
    ).toBeVisible();
    await expect(page.getByRole("textbox", { name: "State" })).toHaveValue(
      "completed",
    );
  });

  test("Confirm bank transfer button is disabled when conditions are not met", async ({
    page,
  }) => {
    const batchOrder = store.list[0];
    batchOrder.state = BatchOrderStatesEnum.BATCH_ORDER_STATE_QUOTED;
    batchOrder.payment_method =
      BatchOrderPaymentMethodEnum.BATCH_ORDER_WITH_BANK_TRANSFER;
    batchOrder.total = 123.45;

    await page.unroute(catchIdRegex);
    await page.route(catchIdRegex, async (route, request) => {
      const methods = request.method();
      if (methods === "GET") {
        await route.fulfill({ json: batchOrder });
      }
    });

    await page.goto(PATH_ADMIN.batch_orders.list);
    await page.getByRole("heading", { name: "Batch Orders" }).click();
    await page
      .getByRole("link", { name: batchOrder.offering.product.title })
      .click();
    await expect(
      page.getByRole("heading", { name: "Batch order informations" }),
    ).toBeVisible();

    // Check and click on the action button
    await expect(page.getByRole("button", { name: "Actions" })).toBeVisible();
    await page.getByRole("button", { name: "Actions" }).click();

    // Confirm bank transfer should be disabled
    const confirmBankTransferMenuItem = page.getByRole("menuitem", {
      name: "Confirm bank transfer",
    });
    await expect(confirmBankTransferMenuItem).toBeVisible();
    await expect(confirmBankTransferMenuItem).toHaveAttribute(
      "aria-disabled",
      "true",
    );
  });

  test("Submit for signature for batch order", async ({ page }) => {
    const batchOrder = store.list[0];
    batchOrder.state = BatchOrderStatesEnum.BATCH_ORDER_STATE_QUOTED;
    batchOrder.total = 123.45;

    const submitForSignatureRegex = new RegExp(
      `${url}${batchOrder.id}/submit-for-signature/`,
    );

    await page.unroute(catchIdRegex);
    await page.route(catchIdRegex, async (route, request) => {
      const methods = request.method();
      if (methods === "GET") {
        await route.fulfill({ json: batchOrder });
      }
    });

    await page.unroute(submitForSignatureRegex);
    await page.route(submitForSignatureRegex, async (route, request) => {
      const methods = request.method();
      if (methods === "POST") {
        batchOrder.state = BatchOrderStatesEnum.BATCH_ORDER_STATE_SIGNING;
        await route.fulfill({ json: batchOrder });
      }
    });

    await page.goto(PATH_ADMIN.batch_orders.list);
    await page.getByRole("heading", { name: "Batch Orders" }).click();
    await page
      .getByRole("link", { name: batchOrder.offering.product.title })
      .click();
    await expect(
      page.getByRole("heading", { name: "Batch order informations" }),
    ).toBeVisible();
    await expect(page.getByRole("textbox", { name: "State" })).toHaveValue(
      "quoted",
    );

    // Check and click on the action button
    await expect(page.getByRole("button", { name: "Actions" })).toBeVisible();
    await page.getByRole("button", { name: "Actions" }).click();

    // Click submit for signature
    await expect(
      page.getByRole("menuitem", { name: "Submit for signature" }),
    ).toBeVisible();
    await page.getByRole("menuitem", { name: "Submit for signature" }).click();

    // Check after operation
    await expect(
      page.getByText(
        "Batch order submitted for signature. Invitation link sent.",
      ),
    ).toBeVisible();
    await expect(page.getByRole("textbox", { name: "State" })).toHaveValue(
      "signing",
    );
  });

  test("Submit for signature button is disabled when conditions are not met", async ({
    page,
  }) => {
    const batchOrder = store.list[0];
    batchOrder.state = BatchOrderStatesEnum.BATCH_ORDER_STATE_DRAFT;
    batchOrder.total = 123.45;

    await page.unroute(catchIdRegex);
    await page.route(catchIdRegex, async (route, request) => {
      const methods = request.method();
      if (methods === "GET") {
        await route.fulfill({ json: batchOrder });
      }
    });

    await page.goto(PATH_ADMIN.batch_orders.list);
    await page.getByRole("heading", { name: "Batch Orders" }).click();
    await page
      .getByRole("link", { name: batchOrder.offering.product.title })
      .click();
    await expect(
      page.getByRole("heading", { name: "Batch order informations" }),
    ).toBeVisible();

    // Check and click on the action button
    await expect(page.getByRole("button", { name: "Actions" })).toBeVisible();
    await page.getByRole("button", { name: "Actions" }).click();

    // Submit for signature should be disabled
    const submitForSignatureMenuItem = page.getByRole("menuitem", {
      name: "Submit for signature",
    });
    await expect(submitForSignatureMenuItem).toBeVisible();
    await expect(submitForSignatureMenuItem).toHaveAttribute(
      "aria-disabled",
      "true",
    );
  });

  test("Generate orders for batch order", async ({ page }) => {
    const batchOrder = store.list[0];
    batchOrder.state = BatchOrderStatesEnum.BATCH_ORDER_STATE_COMPLETED;
    batchOrder.total = 123.45;

    const generateOrdersRegex = new RegExp(
      `${url}${batchOrder.id}/generate-orders/`,
    );

    await page.unroute(catchIdRegex);
    await page.route(catchIdRegex, async (route, request) => {
      const methods = request.method();
      if (methods === "GET") {
        await route.fulfill({ json: batchOrder });
      }
    });

    await page.unroute(generateOrdersRegex);
    await page.route(generateOrdersRegex, async (route, request) => {
      const methods = request.method();
      if (methods === "POST") {
        await route.fulfill({ json: batchOrder });
      }
    });

    await page.goto(PATH_ADMIN.batch_orders.list);
    await page.getByRole("heading", { name: "Batch Orders" }).click();
    await page
      .getByRole("link", { name: batchOrder.offering.product.title })
      .click();
    await expect(
      page.getByRole("heading", { name: "Batch order informations" }),
    ).toBeVisible();
    await expect(page.getByRole("textbox", { name: "State" })).toHaveValue(
      "completed",
    );

    // Check and click on the action button
    await expect(page.getByRole("button", { name: "Actions" })).toBeVisible();
    await page.getByRole("button", { name: "Actions" }).click();

    // Click generate orders
    await expect(
      page.getByRole("menuitem", { name: "Generate orders" }),
    ).toBeVisible();
    await page.getByRole("menuitem", { name: "Generate orders" }).click();

    // Check after operation
    await expect(
      page.getByText(
        "Batch order orders generated. Voucher codes sent to owner.",
      ),
    ).toBeVisible();
  });

  test("Generate orders button is disabled when conditions are not met", async ({
    page,
  }) => {
    const batchOrder = store.list[0];
    batchOrder.state = BatchOrderStatesEnum.BATCH_ORDER_STATE_QUOTED;
    batchOrder.total = 123.45;

    await page.unroute(catchIdRegex);
    await page.route(catchIdRegex, async (route, request) => {
      const methods = request.method();
      if (methods === "GET") {
        await route.fulfill({ json: batchOrder });
      }
    });

    await page.goto(PATH_ADMIN.batch_orders.list);
    await page.getByRole("heading", { name: "Batch Orders" }).click();
    await page
      .getByRole("link", { name: batchOrder.offering.product.title })
      .click();
    await expect(
      page.getByRole("heading", { name: "Batch order informations" }),
    ).toBeVisible();

    // Check and click on the action button
    await expect(page.getByRole("button", { name: "Actions" })).toBeVisible();
    await page.getByRole("button", { name: "Actions" }).click();

    // Generate orders should be disabled
    const generateOrdersMenuItem = page.getByRole("menuitem", {
      name: "Generate orders",
    });
    await expect(generateOrdersMenuItem).toBeVisible();
    await expect(generateOrdersMenuItem).toHaveAttribute(
      "aria-disabled",
      "true",
    );
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
