import { expect, test } from "@playwright/test";
import { faker } from "@faker-js/faker";
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
import {
  ContractDefinition,
  DTOContractDefinition,
} from "@/services/api/models/ContractDefinition";

const searchPlaceholder = "Search by title";

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
    await expect(page.getByPlaceholder(searchPlaceholder)).toBeVisible();
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
      searchTimeout: 200,
      searchResult: productToSearch,
    });
    // Go to the page
    await page.goto(PATH_ADMIN.products.list);
    await expect(page.getByPlaceholder(searchPlaceholder)).toBeVisible();

    await Promise.all(
      store.products.map(async (product) => {
        await expect(page.getByText(product.title)).toBeVisible();
      }),
    );

    await page.getByPlaceholder(searchPlaceholder).click();
    await page.getByPlaceholder(searchPlaceholder).fill(productToSearch.title);
    await expect(page.getByTestId("circular-loader-container")).toBeVisible();
    await expect(page.getByTestId("circular-loader-container")).toBeHidden();
    await expect(page.getByText(productToSearch.title)).toBeVisible();
    await expect(page.getByText(store.products[1].title)).toBeHidden();

    await page.getByPlaceholder(searchPlaceholder).click();
    await page.getByPlaceholder(searchPlaceholder).fill("");
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

    await mockPlaywrightCrud<ContractDefinition, DTOContractDefinition>({
      data: store.contractsDefinitions,
      routeUrl: "http://localhost:8071/api/v1.0/admin/contract-definitions/",
      page,
      searchResult: store.contractsDefinitions[1],
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

    await page.getByPlaceholder("Search a contract definition").click();
    await page
      .getByRole("option", { name: store.contractsDefinitions[0].title })
      .click();
    await expect(
      page.getByText(
        "This is a contract template that will be used when purchasing the product",
      ),
    ).toBeVisible();

    const cta = page.getByLabel("Call to action *");
    await cta.click();
    await cta.fill("Test product");

    await page.getByRole("button", { name: "Submit" }).click();
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

  test("Create a new contract definition with the search input", async ({
    page,
  }) => {
    await mockPlaywrightCrud<ContractDefinition, DTOContractDefinition>({
      data: store.contractsDefinitions,
      routeUrl: "http://localhost:8071/api/v1.0/admin/contract-definitions/",
      page,
      createCallback: (payload) => {
        const contract: ContractDefinition = {
          ...payload,
          id: faker.string.uuid(),
        };
        store.contractsDefinitions.push(contract);
        return contract;
      },
      searchResult: store.contractsDefinitions[1],
    });
    // Go to the page
    await page.goto(PATH_ADMIN.products.list);
    await page.getByRole("button", { name: "Add" }).click();
    await page.getByText("Microcredential", { exact: true }).click();
    await page.getByTestId("search-add-button").nth(1).click();
    await expect(
      page.getByRole("heading", { name: "close Add a contract" }),
    ).toBeVisible();
    await page.getByLabel("Title", { exact: true }).click();
    await page.getByLabel("Title", { exact: true }).fill("Test contract");
    await page.getByLabel("Description", { exact: true }).click();
    await page
      .getByLabel("Description", { exact: true })
      .fill("Test contract desc");
    await page
      .getByLabel("Add a contract definition")
      .getByTestId("md-editor")
      .getByRole("textbox")
      .click();
    await page
      .getByLabel("Add a contract definition")
      .getByTestId("md-editor")
      .getByRole("textbox")
      .fill("> Body");
    await page.getByTestId("submit-button-contract-definition-form").click();
    await expect(
      page.getByRole("heading", { name: "Add a contract" }),
    ).toBeHidden();
    await expect(
      page.getByPlaceholder("Search a contract definition"),
    ).toHaveValue("Test contract");
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

    await expect(
      addTargetCourseModal
        .getByTestId("product-target-course-runs-selection-alert")
        .getByText(
          "By default all course runs are selected, turn this switch on if you want to choose which course runs are selected.",
        ),
    ).toBeVisible();

    await addTargetCourseModal
      .getByTestId("product-target-course-runs-selection-alert")
      .getByTestId("enable-course-runs-selection")
      .click();

    await page
      .getByRole("row", { name: `Select row ${courseRuns[0].title} Click` })
      .getByLabel("Select row")
      .check();
    await page.getByTestId("submit-button-product-target-course-form").click();

    const dummyTargetCourseLocator = page.getByTestId(
      `dummy-product-target-course-${course.id}`,
    );

    const targetCourseLocator = page.getByTestId(
      `item-product-target-course-${course.id}`,
    );
    await expect(dummyTargetCourseLocator).toBeHidden();
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
  test("Check all course product relations", async ({ page }) => {
    const product = store.products[0];
    product.target_courses = [];
    const relations = product.course_relations!;

    await mockPlaywrightCrud<Course, DTOCourse>({
      data: [relations[0].course],
      routeUrl: "http://localhost:8071/api/v1.0/admin/courses/",
      page,
      optionsResult: COURSE_OPTIONS_REQUEST_RESULT,
    });

    await page.goto(PATH_ADMIN.products.list);
    await expect(page.getByRole("heading", { name: "Products" })).toBeVisible();
    await page.getByRole("link", { name: product.title }).click();
    await page
      .getByRole("heading", {
        name: "List of courses to which this product is linked",
      })
      .click();
    await expect(
      page
        .getByTestId("product-course-relation-alert")
        .getByText(
          "In this section, you have access to all courses to which this product is attached. Click on the course title to navigate to its detail.",
        ),
    ).toBeVisible();
    await Promise.all(
      relations.map(async (relation) => {
        await expect(
          page.getByRole("heading", { name: relation.course.title }),
        ).toBeVisible();
        await expect(
          page.getByRole("link", { name: relation.course.title }),
        ).toBeVisible();
        await expect(
          page.getByText(
            relation.organizations.map((org) => org.title).join(","),
          ),
        ).toBeVisible();
      }),
    );

    // Test click on course title and open another tab
    await page.getByRole("link", { name: relations[0].course.title }).click();
    await page.route(
      `http://localhost:8071/api/v1.0/admin/courses/${relations[0].course.id}/?`,
      async (route, request) => {
        const methods = request.method();
        if (methods === "GET") {
          await route.fulfill({ json: relations[0].course });
        }
      },
    );

    await expect(
      page.getByRole("heading", {
        name: `Edit course: ${relations[0].course.title}`,
      }),
    ).toBeVisible();
  });

  test("Copy url inside the clipboard", async ({ page, context }) => {
    await context.grantPermissions(["clipboard-read", "clipboard-write"]);
    const product = store.products[0];
    product.target_courses = [];
    const relations = product.course_relations!;

    await mockPlaywrightCrud<Course, DTOCourse>({
      data: [relations[0].course],
      routeUrl: "http://localhost:8071/api/v1.0/admin/courses/",
      page,
      optionsResult: COURSE_OPTIONS_REQUEST_RESULT,
    });

    await page.goto(PATH_ADMIN.products.list);
    await expect(page.getByRole("heading", { name: "Products" })).toBeVisible();
    await page.getByRole("link", { name: product.title }).click();

    await page
      .getByTestId(`course-product-relation-actions-${relations[0].id}`)
      .click();

    await page.getByRole("menuitem", { name: "Copy url" }).click();
    await expect(
      page.getByRole("alert").getByText("Link added to your clipboard"),
    ).toBeVisible();
    const handle = await page.evaluateHandle(() =>
      navigator.clipboard.readText(),
    );
    const clipboardContent = await handle.jsonValue();
    expect(clipboardContent).toEqual(relations[0].uri);
  });
});
