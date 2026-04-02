import { expect, test } from "@playwright/test";
import {
  getUrlCatchSearchParamsRegex,
  mockPlaywrightCrud,
} from "@/tests/useResourceHandler";
import { PATH_ADMIN } from "@/utils/routes/path";
import {
  DTOOffering,
  Offering,
  OfferingFactory,
} from "@/services/api/models/Offerings";
import { OrganizationFactory } from "@/services/factories/organizations";

test.describe("Order create form", () => {
  const singleOrgOffering = OfferingFactory();
  singleOrgOffering.product.title = "Single Org Product";
  singleOrgOffering.course.title = "Single Org Course";
  singleOrgOffering.organizations = [OrganizationFactory()];

  const multiOrgOffering = OfferingFactory();
  multiOrgOffering.product.title = "Multi Org Product";
  multiOrgOffering.course.title = "Multi Org Course";
  multiOrgOffering.organizations = [
    OrganizationFactory(),
    OrganizationFactory(),
  ];
  multiOrgOffering.organizations[0].title = "Org Alpha";
  multiOrgOffering.organizations[1].title = "Org Beta";

  test.beforeEach(async ({ page }) => {
    await mockPlaywrightCrud<Offering, DTOOffering>({
      data: [singleOrgOffering, multiOrgOffering],
      routeUrl: "http://localhost:8071/api/v1.0/admin/offerings/",
      page,
      searchResult: [singleOrgOffering, multiOrgOffering],
    });

    const ordersUrl = "http://localhost:8071/api/v1.0/admin/orders/";
    const queryParamsRegex = getUrlCatchSearchParamsRegex(ordersUrl);
    await page.unroute(queryParamsRegex);
    await page.route(queryParamsRegex, async (route, request) => {
      if (request.method() === "GET") {
        await route.fulfill({
          json: { count: 0, results: [], next: null, previous: null },
        });
      }
      if (request.method() === "POST") {
        await route.fulfill({ status: 201, json: { id: "fake-id" } });
      }
    });
  });

  test("Organization field is required when multiple organizations", async ({
    page,
  }) => {
    await page.goto(PATH_ADMIN.orders.create);
    await expect(
      page.getByRole("heading", { name: "Add order" }),
    ).toBeVisible();

    // Select offering with multiple orgs
    const offeringCombobox = await page.getByRole("combobox", {
      name: "Offering",
    });
    await offeringCombobox.click();
    await offeringCombobox.fill("Multi");
    await page
      .getByRole("option", { name: "Multi Org Product — Multi Org Course" })
      .click();

    // Organization field should be visible
    await expect(page.getByLabel("Organization")).toBeVisible();

    // Submit without selecting organization
    await page.getByRole("button", { name: "Submit" }).click();

    // Should show validation error
    await expect(
      page.getByText("organization is a required field"),
    ).toBeVisible();
  });
});
