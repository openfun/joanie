import { expect, test } from "@playwright/test";
import { getOrdersScenarioStore } from "@/tests/orders/OrderTestScenario";
import {
  getUrlCatchSearchParamsRegex,
  mockPlaywrightCrud,
} from "@/tests/useResourceHandler";
import { transformOrdersToOrderListItems } from "@/services/api/models/Order";
import { PATH_ADMIN } from "@/utils/routes/path";
import { Course, DTOCourse } from "@/services/api/models/Course";
import { DTOProduct, ProductSimple } from "@/services/api/models/Product";
import {
  DTOOrganization,
  Organization,
} from "@/services/api/models/Organization";
import { User } from "@/services/api/models/User";
import { ORGANIZATION_OPTIONS_REQUEST_RESULT } from "@/tests/mocks/organizations/organization-mock";
import { COURSE_OPTIONS_REQUEST_RESULT } from "@/tests/mocks/courses/course-mocks";

test.describe("Order filters", () => {
  let store = getOrdersScenarioStore();
  test.beforeEach(async ({ page }) => {
    const url = "http://localhost:8071/api/v1.0/admin/orders/";
    store = getOrdersScenarioStore();
    const list = transformOrdersToOrderListItems(store.list);
    const queryParamsRegex = getUrlCatchSearchParamsRegex(url);
    await page.unroute(queryParamsRegex);
    await page.route(queryParamsRegex, async (route, request) => {
      const methods = request.method();
      if (methods === "GET") {
        await route.fulfill({ json: list });
      }
    });

    await mockPlaywrightCrud<ProductSimple, DTOProduct>({
      data: store.products,
      routeUrl: "http://localhost:8071/api/v1.0/admin/products/",
      page,
      searchResult: store.products[0],
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

    await mockPlaywrightCrud<Course, DTOCourse>({
      data: store.courses,
      routeUrl: "http://localhost:8071/api/v1.0/admin/courses/",
      page,
      searchResult: store.courses[0],
      optionsResult: COURSE_OPTIONS_REQUEST_RESULT,
    });
  });

  test("Check all field are presents", async ({ page }) => {
    await page.goto(PATH_ADMIN.orders.list);
    await expect(page.getByRole("heading", { name: "Orders" })).toBeVisible();
    await expect(
      page.getByPlaceholder("Search by product title,"),
    ).toBeVisible();
    await page.getByRole("button", { name: "Filters" }).click();
    await expect(
      page.getByTestId("select-order-state-filter").getByLabel("State"),
    ).toBeVisible();
    await expect(page.getByRole("combobox", { name: "Product" })).toBeVisible();
    await expect(page.getByLabel("Course")).toBeVisible();
    await expect(page.getByRole("combobox", { name: "Owner" })).toBeVisible();
    await expect(
      page.getByRole("combobox", { name: "Organization" }),
    ).toBeVisible();
  });

  test("Check all chips", async ({ page }) => {
    await page.goto(PATH_ADMIN.orders.list);
    await expect(page.getByRole("heading", { name: "Orders" })).toBeVisible();
    await page.getByRole("button", { name: "Filters" }).click();
    await page
      .getByTestId("select-order-state-filter")
      .getByLabel("State")
      .click();
    await page.getByRole("option", { name: "Completed" }).click();
    await page.getByTestId("custom-modal").getByLabel("Product").click();

    await page.getByTestId("custom-modal").getByLabel("Product").fill("p");
    await page.getByRole("option", { name: store.products[0].title }).click();
    await page.getByLabel("Course").click();
    await page.getByLabel("Course").fill("c");
    await page.getByRole("option", { name: store.courses[0].title }).click();
    await page.getByRole("combobox", { name: "Organization" }).click();
    await page.getByRole("combobox", { name: "Organization" }).fill("o");
    await page
      .getByRole("option", { name: store.organizations[0].title })
      .click();
    await page.getByRole("combobox", { name: "Owner" }).click();
    await page.getByRole("combobox", { name: "Owner" }).fill("u");
    await page.getByRole("option", { name: store.users[0].username }).click();
    await page.getByLabel("close").click();
    await expect(
      page.getByRole("button", { name: "State: Completed" }),
    ).toBeVisible();
    await expect(
      page.getByRole("button", { name: `Product: ${store.products[0].title}` }),
    ).toBeVisible();
    await expect(
      page.getByRole("button", { name: `Course: ${store.courses[0].title}` }),
    ).toBeVisible();
    await expect(
      page.getByRole("button", {
        name: `Organization: ${store.organizations[0].title}`,
      }),
    ).toBeVisible();
    await expect(
      page.getByRole("button", { name: `Owner: ${store.users[0].username}` }),
    ).toBeVisible();
  });
});
