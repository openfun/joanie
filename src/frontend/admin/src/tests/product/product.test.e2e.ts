import { expect, test } from "@playwright/test";
import { mockPlaywrightCrud } from "../useResourceHandler";
import { getProductScenarioStore } from "./ProductTestScenario";
import { PATH_ADMIN } from "@/utils/routes/path";

import { DTOProduct, Product } from "@/services/api/models/Product";
import {
  CertificateDefinition,
  DTOCertificateDefinition,
} from "@/services/api/models/CertificateDefinition";

test.describe("Product list", () => {
  const store = getProductScenarioStore();
  test.beforeEach(async ({ page }) => {
    await mockPlaywrightCrud<Product, DTOProduct>({
      data: store.products,
      routeUrl: "http://localhost:8071/api/v1.0/admin/products/",
      page,
    });
  });

  test("verify all products are inside the list", async ({ page }) => {
    // Go to the page
    await page.goto(PATH_ADMIN.products.list);
    await expect(page.getByPlaceholder("Search...")).toBeVisible();
    await Promise.all(
      store.products.map(async (product) => {
        await expect(page.getByText(product.title)).toBeVisible();
      }),
    );
  });

  test("search product in list", async ({ page }) => {
    // Go to the page
    await page.goto(PATH_ADMIN.products.list);
    await expect(page.getByPlaceholder("Search...")).toBeVisible();

    await Promise.all(
      store.products.map(async (product) => {
        await expect(page.getByText(product.title)).toBeVisible();
      }),
    );

    await page.getByPlaceholder("Search...").click();
    await page.getByPlaceholder("Search...").fill("search");
    await expect(page.getByTestId("circular-loader-container")).toBeVisible();
    await expect(page.getByTestId("circular-loader-container")).toBeHidden();
    await expect(page.getByText(store.products[0].title)).toBeVisible();
    await expect(page.getByText(store.products[1].title)).toBeHidden();

    await page.getByPlaceholder("Search...").click();
    await page.getByPlaceholder("Search...").fill("");
    await Promise.all(
      store.products.map(async (product) => {
        await expect(page.getByText(product.title)).toBeVisible();
      }),
    );
  });
});

test.describe("Product create", () => {
  const store = getProductScenarioStore();
  test("Create a new product", async ({ page }) => {
    await mockPlaywrightCrud<CertificateDefinition, DTOCertificateDefinition>({
      data: store.certificateDefinitions,
      routeUrl: "http://localhost:8071/api/v1.0/admin/certificate-definitions/",
      page,
      searchResult: store.certificateDefinitions[1],
    });

    await mockPlaywrightCrud<Product, DTOProduct>({
      data: store.products,
      routeUrl: "http://localhost:8071/api/v1.0/admin/products/",
      page,
      createCallback: store.postUpdate,
    });

    // Go to the page
    await page.goto(PATH_ADMIN.products.list);
    await Promise.all(
      store.products.map(async (product) => {
        await expect(page.getByText(product.title)).toBeVisible();
      }),
    );

    await page.getByRole("button", { name: "Add" }).click();
    await page.getByText("Microcredential", { exact: true }).click();
    const title = page.getByRole("textbox", { name: "title" });
    await title.click();
    await title.fill("Test product");

    const description = page.getByRole("textbox", { name: "description" });
    await description.click();
    await description.fill("Description");

    await page.getByLabel("Certificate definition").click();
    await page
      .getByRole("option", { name: store.certificateDefinitions[1].title })
      .click();

    const cta = page.getByLabel("Call to action *");
    await cta.click();
    await cta.fill("Test product");
    await expect(
      page.getByText("Operation completed successfully."),
    ).toBeVisible();
    await page.getByRole("link", { name: "List" }).click();
    await expect(page.getByText("Test product")).toBeVisible();
  });
});
