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
  OrderStatesEnum,
  transformOrdersToOrderListItems,
} from "@/services/api/models/Order";
import { PATH_ADMIN } from "@/utils/routes/path";
import { getOrderListItemsScenarioStore } from "@/tests/orders/OrderListItemTestScenario";
import {
  DTOOrganization,
  Organization,
} from "@/services/api/models/Organization";
import { ORGANIZATION_OPTIONS_REQUEST_RESULT } from "@/tests/mocks/organizations/organization-mock";
import { closeAllNotification, delay } from "@/components/testing/utils";
import { formatShortDateTest } from "@/tests/utils";
import { orderStatesMessages } from "@/components/templates/orders/view/translations";

const url = "http://localhost:8071/api/v1.0/admin/orders/";
const catchIdRegex = getUrlCatchIdRegex(url);
const queryParamsRegex = getUrlCatchSearchParamsRegex(url);
test.describe("Order view", () => {
  let store = getOrdersScenarioStore();
  test.beforeEach(async ({ page }) => {
    store = getOrdersScenarioStore();
    const list = transformOrdersToOrderListItems(store.list);

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
    const order = store.list[0];
    order.main_invoice.created_on = new Date(
      Date.UTC(2024, 0, 23, 19, 30),
    ).toLocaleString("en-US");
    order.main_invoice.updated_on = new Date(
      Date.UTC(2024, 0, 23, 20, 30),
    ).toLocaleString("en-US");
    await page.goto(PATH_ADMIN.orders.list);
    await page.getByRole("heading", { name: "Orders" }).click();
    await page.getByRole("link", { name: order.product.title }).click();

    await page.getByRole("heading", { name: "Order informations" }).click();
    await expect(page.getByLabel("Organization", { exact: true })).toHaveValue(
      order.organization?.title ?? "",
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

    await expect(page.getByLabel("Created on")).toHaveValue("1/23/24, 7:30 PM");

    await expect(page.getByLabel("Updated on")).toHaveValue("1/23/24, 8:30 PM");
    await expect(page.getByLabel("Balance")).toHaveValue(
      order.main_invoice.balance,
    );
    if (order.certificate) {
      await expect(page.getByLabel("Certificate", { exact: true })).toHaveValue(
        order.certificate.definition_title,
      );
    }

    await expect(
      page.getByRole("heading", { name: "Payment schedule" }),
    ).toBeVisible();
    const paymentSchedule = order.payment_schedule;
    if (paymentSchedule) {
      await Promise.all(
        paymentSchedule!.map(async (payment) => {
          const paymentLocator = page.getByTestId(
            `order-view-payment-${payment.id}`,
          );
          await page.pause();
          await expect(paymentLocator).toBeVisible();
          await expect(
            paymentLocator.getByRole("cell", {
              name: await formatShortDateTest(page, payment.due_date),
            }),
          ).toBeVisible();
          await expect(
            paymentLocator.getByRole("cell", {
              name: payment.amount.toString() + " " + payment.currency,
            }),
          ).toBeVisible();
          await expect(
            paymentLocator.getByRole("cell", { name: payment.state }),
          ).toBeVisible();
        }),
      );
    }

    if (order.credit_card) {
      const creditCardLocator = page.getByTestId(
        `credit-card-${order.credit_card!.id}`,
      );
      await expect(creditCardLocator).toBeVisible();
    }
  });

  test("Check when organization is undefined", async ({ page }) => {
    const order = store.list[0];
    order.main_invoice.created_on = new Date(
      Date.UTC(2024, 0, 23, 19, 30),
    ).toLocaleString("en-US");
    order.main_invoice.updated_on = new Date(
      Date.UTC(2024, 0, 23, 20, 30),
    ).toLocaleString("en-US");
    order.organization = undefined;
    await page.unroute(catchIdRegex);
    await page.route(catchIdRegex, async (route, request) => {
      const methods = request.method();
      if (methods === "GET") {
        await route.fulfill({ json: store.list[0] });
      }
    });
    await page.goto(PATH_ADMIN.orders.list);
    await page.getByRole("heading", { name: "Orders" }).click();
    await page.getByRole("link", { name: order.product.title }).click();

    await page.getByRole("heading", { name: "Order informations" }).click();
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
    await expect(
      page.getByLabel("Organization", { exact: true }),
    ).toBeVisible();
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
      await expect(
        page.getByLabel("Certificate", { exact: true }),
      ).toBeVisible();
    }
    if (order.has_waived_withdrawal_right) {
      await expect(
        page.getByText("The user has waived its withdrawal right."),
      ).toBeVisible();
    } else {
      await expect(
        page.getByText("The user has not waived its withdrawal right."),
      ).toBeVisible();
    }
  });
  test("Check all contract fields field are in this view", async ({ page }) => {
    const order = store.list[0];
    await page.goto(PATH_ADMIN.orders.list);
    await page.getByRole("heading", { name: "Orders" }).click();
    await page.getByRole("link", { name: order.product.title }).click();

    await expect(
      page.getByRole("heading", { name: "Contract details" }),
    ).toBeVisible();

    // Contract field
    const contract = page.getByTestId("order-view-contract-name");
    await expect(contract.getByLabel("Contract")).toBeVisible();
    await expect(contract.getByTestId("RemoveRedEyeIcon")).toBeVisible();

    // Start of signing field
    const startSigningField = page.getByTestId(
      "order-view-contract-submitted-for-signature",
    );
    await expect(
      startSigningField.getByLabel("Submit for signature"),
    ).toBeVisible();

    // Studient signature date field
    const student = page.getByTestId("order-view-contract-student-signed-on");
    await expect(student.getByLabel("Student signature date")).toBeVisible();
    await expect(student.getByTestId("TaskAltIcon")).toBeVisible();

    // Organization signature date field
    const organization = page.getByTestId(
      "order-view-contract-organization-signed-on",
    );
    await expect(
      organization.getByLabel("Organization signature date"),
    ).toBeVisible();
    await expect(organization.getByTestId("TaskAltIcon")).toBeVisible();
  });

  test("Check contract signature field icons when no signing has occurred", async ({
    page,
  }) => {
    const order = store.list[0];
    order.contract!.student_signed_on = null;
    order.contract!.organization_signed_on = null;
    order.contract!.submitted_for_signature_on = null;

    await page.unroute(catchIdRegex);
    await page.route(catchIdRegex, async (route, request) => {
      const methods = request.method();
      if (methods === "GET") {
        await route.fulfill({ json: order });
      }
    });
    await page.goto(PATH_ADMIN.orders.list);
    await page.getByRole("heading", { name: "Orders" }).click();
    await page.getByRole("link", { name: order.product.title }).click();

    await expect(
      page.getByRole("heading", { name: "Contract details" }),
    ).toBeVisible();

    // Studient signature date field
    const student = page.getByTestId("order-view-contract-student-signed-on");
    await expect(student.getByTestId("HighlightOffIcon")).toBeVisible();

    // Organization signature date field
    const organization = page.getByTestId(
      "order-view-contract-organization-signed-on",
    );
    await expect(organization.getByTestId("HighlightOffIcon")).toBeVisible();
  });

  test("Cancel order", async ({ page }) => {
    const order = store.list[0];
    order.state = OrderStatesEnum.ORDER_STATE_DRAFT;

    await page.unroute(catchIdRegex);
    await page.route(catchIdRegex, async (route, request) => {
      const methods = request.method();
      if (methods === "GET") {
        await route.fulfill({ json: order });
      }

      if (methods === "DELETE") {
        order.state = OrderStatesEnum.ORDER_STATE_CANCELED;
        await route.fulfill({ json: order });
      }
    });
    await page.goto(PATH_ADMIN.orders.list);
    await page.getByRole("heading", { name: "Orders" }).click();
    await page.getByRole("link", { name: order.product.title }).click();
    await expect(
      page.getByRole("heading", { name: "Order informations" }),
    ).toBeVisible();
    await expect(page.getByRole("textbox", { name: "State" })).toHaveValue(
      "Draft",
    );

    // Check and click on the action button
    await expect(page.getByRole("button", { name: "Actions" })).toBeVisible();
    await page.getByRole("button", { name: "Actions" }).click();

    // Cancel order

    await expect(
      page.getByRole("menuitem", { name: "Cancel this order" }),
    ).toBeVisible();
    await page.getByRole("menuitem", { name: "Cancel this order" }).click();

    // Check after operation
    await expect(page.getByText("Operation completed")).toBeVisible();
    await expect(page.getByRole("textbox", { name: "State" })).toHaveValue(
      "Canceled",
    );
  });

  test("Refund order", async ({ page }) => {
    const order = store.list[0];
    order.state = OrderStatesEnum.ORDER_STATE_CANCELED;

    await page.unroute(catchIdRegex);
    await page.route(catchIdRegex, async (route, request) => {
      const methods = request.method();
      if (methods === "GET") {
        await route.fulfill({ json: order });
      }
    });
    await page.goto(PATH_ADMIN.orders.list);
    await page.getByRole("heading", { name: "Orders" }).click();
    await page.getByRole("link", { name: order.product.title }).click();
    await expect(
      page.getByRole("heading", { name: "Order informations" }),
    ).toBeVisible();
    await expect(page.getByRole("textbox", { name: "State" })).toHaveValue(
      "Canceled",
    );

    // Check and click on the action button
    await expect(page.getByRole("button", { name: "Actions" })).toBeVisible();
    await page.getByRole("button", { name: "Actions" }).click();

    // Refund order
    await page.route(
      `http://localhost:8071/api/v1.0/admin/orders/${order.id}/refund/`,
      async (route, request) => {
        const methods = request.method();
        if (methods === "POST") {
          order.state = OrderStatesEnum.ORDER_STATE_REFUNDING;
          await route.fulfill();
        }
      },
    );
    await page.unroute(catchIdRegex);
    await page.route(catchIdRegex, async (route, request) => {
      const methods = request.method();
      if (methods === "GET") {
        await route.fulfill({ json: order });
      }
    });

    await expect(
      page.getByRole("menuitem", { name: "Refund this order" }),
    ).toBeVisible();
    await page.getByRole("menuitem", { name: "Refund this order" }).click();

    // Check after operation
    await expect(page.getByText("Refunding order.")).toBeVisible();
    await expect(page.getByRole("textbox", { name: "State" })).toHaveValue(
      "Refunding",
    );
  });

  test("Generate certificate", async ({ page }) => {
    const order = store.list[0];
    order.certificate = null;
    order.state = OrderStatesEnum.ORDER_STATE_COMPLETED;

    await page.unroute(catchIdRegex);
    await page.route(catchIdRegex, async (route, request) => {
      const methods = request.method();
      if (methods === "GET") {
        await route.fulfill({ json: order });
      }

      if (methods === "DELETE") {
        order.state = OrderStatesEnum.ORDER_STATE_CANCELED;
        await route.fulfill({ json: order });
      }
    });
    await page.goto(PATH_ADMIN.orders.list);
    await page.getByRole("heading", { name: "Orders" }).click();
    await page.getByRole("link", { name: order.product.title }).click();
    await expect(
      page.getByRole("heading", { name: "Order informations" }),
    ).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Certificate details" }),
    ).not.toBeVisible();

    // Check and click on the action button
    const actionsMenuButton = page.getByRole("button", { name: "Actions" });
    await expect(actionsMenuButton).toBeVisible();
    await actionsMenuButton.click();

    await page.route(
      `http://localhost:8071/api/v1.0/admin/orders/${order.id}/generate_certificate/`,
      async (route, request) => {
        const methods = request.method();
        if (methods === "POST") {
          await route.fulfill({
            json: {
              definition_title: "Certificate definition",
              id: "e4c5c271-5695-4e29-a381-09e3c1635e74",
              issued_on: "2024-03-25T14:00:00.034185 +00:00",
            },
          });
        }
      },
    );

    order.certificate = {
      definition_title: "Certificate definition",
      id: "e4c5c271-5695-4e29-a381-09e3c1635e74",
      issued_on: "2024-03-25T14:00:00.034185Z",
    };
    await page.unroute(catchIdRegex);
    await page.route(catchIdRegex, async (route, request) => {
      const methods = request.method();
      if (methods === "GET") {
        await route.fulfill({ json: order });
      }
    });

    // // Cancel order
    //
    const generateCertificateAction = page.getByRole("menuitem", {
      name: "Generate certificate",
    });
    await expect(generateCertificateAction).toBeVisible();
    await generateCertificateAction.click();
    //
    // // Check after operation
    await expect(
      page.getByText("Certificate successfully generated"),
    ).toBeVisible();

    // Check the certificate details sections
    await expect(
      page.getByRole("heading", { name: "Certificate details" }),
    ).toBeVisible();

    const certificateName = page.getByLabel("Certificate template");
    await expect(certificateName).toBeVisible();
    await expect(certificateName).toHaveValue("Certificate definition");

    const generatedDate = page.getByLabel("Issuance date");
    await expect(generatedDate).toBeVisible();
    await expect(generatedDate).toHaveValue("3/25/24, 2:00 PM");

    await closeAllNotification(page);
    await actionsMenuButton.click();
    await page.getByTestId("Generate certificate").hover();
    await delay(200);

    await expect(
      page.getByText("The certificate has already been generated"),
    ).toBeVisible();
  });

  test("should display alert message when order has no credit card", async ({
    page,
  }) => {
    const order = store.list[0];
    order.credit_card = null;

    await page.unroute(catchIdRegex);
    await page.route(catchIdRegex, async (route, request) => {
      const methods = request.method();
      if (methods === "GET") {
        await route.fulfill({ json: order });
      }
    });
    await page.goto(PATH_ADMIN.orders.list);
    await page.getByRole("link", { name: order.product.title }).click();

    await expect(
      page.getByRole("alert").getByText("No payment method has been defined."),
    ).toBeVisible();
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
    await expect(
      page.getByRole("columnheader", { name: "Created on" }),
    ).toBeVisible();
    await expect(
      page.getByRole("columnheader", { name: "Updated on" }),
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
          rowLocator.getByRole("gridcell", { name: order.organization_title }),
        ).toBeVisible();
        await expect(
          rowLocator.getByRole("gridcell", { name: order.owner_name }),
        ).toBeVisible();
        await expect(
          rowLocator.getByRole("gridcell", { name: order.product_title }),
        ).toBeVisible();
        await expect(
          rowLocator.getByRole("gridcell", {
            name: orderStatesMessages[order.state].defaultMessage,
          }),
        ).toBeVisible();
        await expect(
          rowLocator.getByRole("gridcell", {
            name: await formatShortDateTest(page, order.created_on),
          }),
        ).toBeVisible();
        await expect(
          rowLocator.getByRole("gridcell", {
            name: await formatShortDateTest(page, order.updated_on),
          }),
        ).toBeVisible();
      }),
    );
  });
});
