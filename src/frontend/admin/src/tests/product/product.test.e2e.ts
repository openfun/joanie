import { expect, test } from "@playwright/test";
import { mockPlaywrightCrud } from "../useResourceHandler";
import {
  getProductScenarioStore,
  mockTargetCourses,
} from "./ProductTestScenario";
import { PATH_ADMIN } from "@/utils/routes/path";

import { DTOProduct, Product } from "@/services/api/models/Product";
import {
  CertificateDefinition,
  DTOCertificateDefinition,
} from "@/services/api/models/CertificateDefinition";
import { Course, DTOCourse } from "@/services/api/models/Course";
import { mockCourseRunsFromCourse } from "@/tests/mocks/course-runs/course-runs-mocks";
import { CourseRun } from "@/services/api/models/CourseRun";
import { COURSE_OPTIONS_REQUEST_RESULT } from "@/tests/mocks/courses/course-mocks";

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
    const productToSearch = store.products[0];
    await mockPlaywrightCrud<Product, DTOProduct>({
      data: store.products,
      routeUrl: "http://localhost:8071/api/v1.0/admin/products/",
      page,
      searchTimeout: 150,
      searchResult: productToSearch,
    });
    // Go to the page
    await page.goto(PATH_ADMIN.products.list);
    await expect(page.getByPlaceholder("Search...")).toBeVisible();

    await Promise.all(
      store.products.map(async (product) => {
        await expect(page.getByText(product.title)).toBeVisible();
      }),
    );

    await page.getByPlaceholder("Search...").click();
    await page.getByPlaceholder("Search...").fill(productToSearch.title);
    await expect(page.getByTestId("circular-loader-container")).toBeVisible();
    await expect(page.getByTestId("circular-loader-container")).toBeHidden();
    await expect(page.getByText(productToSearch.title)).toBeVisible();
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

test.describe("Product form", () => {
  let store = getProductScenarioStore();
  test.beforeEach(async ({ page }) => {
    store = getProductScenarioStore();
    await mockPlaywrightCrud<Course, DTOCourse>({
      data: store.courses,
      optionsResult: COURSE_OPTIONS_REQUEST_RESULT,
      routeUrl: "http://localhost:8071/api/v1.0/admin/courses/",
      page,
    });

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
  });

  test("Create a new product", async ({ page }) => {
    // Go to the page
    await page.goto(PATH_ADMIN.products.list);
    await page.getByRole("button", { name: "Add" }).click();
    await page.getByText("Microcredential", { exact: true }).click();
    const title = page.getByRole("textbox", { name: "title" });
    await expect(page.getByRole("button", { name: "Next" })).toHaveCount(0);
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

    await expect(
      page.getByRole("heading", { name: "Edit product: Test product" }),
    ).toBeVisible();
    await expect(page.getByRole("button", { name: "Back" })).toHaveCount(1);
    await expect(page.getByRole("button", { name: "Back" })).toBeDisabled();
    await expect(page.getByRole("button", { name: "Next" })).toHaveCount(1);
    await expect(page.getByRole("button", { name: "Next" })).not.toBeDisabled();

    // Add Target Course

    await page.getByRole("link", { name: "List" }).click();
    await expect(page.getByText("Test product")).toBeVisible();
  });

  test("Create and edit target course", async ({ page }) => {
    const product = store.products[0];
    product.target_courses = [];
    await page.goto(PATH_ADMIN.products.list);
    await expect(page.getByRole("heading", { name: "Products" })).toBeVisible();

    await page.getByRole("link", { name: product.title }).click();
    await page.getByRole("button", { name: "Next" }).click();
    await expect(
      page
        .locator("#product-target-courses-form")
        .getByRole("alert")
        .getByText(
          "In this part, you can choose the courses contained in the product, as well as all the associated course sessions",
        ),
    ).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Product target courses" }),
    ).toBeVisible();
    await expect(page.getByText("No target course has been")).toBeVisible();
    await expect(page.getByRole("button", { name: "Next" })).toBeDisabled();
    await page.getByRole("button", { name: "Add target course" }).click();
    const addTargetCourseModal = page.getByTestId("add-target-course-modal");
    await expect(
      addTargetCourseModal
        .getByRole("alert")
        .getByText(
          "In this form, you can choose a course to integrate into the product as well as the associated course paths. If you do not select any race runs, they will all be selected by default.",
        ),
    ).toBeVisible();

    const course = store.courses[0];
    const courseRuns = course.courses_runs as CourseRun[];
    await mockCourseRunsFromCourse(page, courseRuns);
    await mockTargetCourses(
      page,
      store.targetCourses,
      store.products,
      store.courses,
      courseRuns,
    );
    await page.getByLabel("Course search").click();
    await page.getByLabel("Course search").fill(course.title);
    await page.getByRole("option", { name: course.title }).click();

    await page
      .getByRole("row", { name: `Select row ${courseRuns[0].title} Click` })
      .getByLabel("Select row")
      .check();
    await page.getByTestId("submit-button-product-target-course-form").click();

    const targetCourseLocator = page.getByTestId(
      `product-target-course-${course.id}`,
    );
    await expect(targetCourseLocator).toBeVisible();
    await expect(
      targetCourseLocator.getByRole("heading", { name: course.title }),
    ).toBeVisible();
    await expect(
      targetCourseLocator.getByText("1 course runs selected."),
    ).toBeVisible();

    await targetCourseLocator.hover();
    await targetCourseLocator.getByTestId("edit-row-button").click();
    await expect(
      page.getByRole("heading", { name: "Add target courses" }),
    ).toBeVisible();

    await page
      .getByRole("row", { name: `Unselect row ${courseRuns[0].title}` })
      .getByLabel("Unselect row")
      .uncheck();
    await page.getByTestId("submit-button-product-target-course-form").click();
    await expect(
      targetCourseLocator.getByText("All selected course_runs."),
    ).toBeVisible();
  });
});
