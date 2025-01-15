import { expect, test } from "@playwright/test";
import { faker } from "@faker-js/faker";
import { mockPlaywrightCrud } from "../useResourceHandler";
import { CONTRACT_DEFINITION_OPTIONS_REQUEST_RESULT } from "../mocks/contract-definitions/contract-definition-mocks";
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
import { ProductTargetCourseRelationFactory } from "@/services/api/models/ProductTargetCourseRelation";
import { delay } from "@/components/testing/utils";
import { DTOSkill, Skill } from "@/services/api/models/Skill";
import { DTOTeacher, Teacher } from "@/services/api/models/Teacher";

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

    await mockPlaywrightCrud<Skill, DTOSkill>({
      data: store.skills,
      routeUrl: "http://localhost:8071/api/v1.0/admin/skills/",
      page,
      searchResult: store.skills[1],
      createCallback: store.updateOrCreateSkill,
      updateCallback: store.updateOrCreateSkill,
    });

    await mockPlaywrightCrud<Teacher, DTOTeacher>({
      data: store.teachers,
      routeUrl: "http://localhost:8071/api/v1.0/admin/teachers/",
      page,
      searchResult: store.teachers[1],
      createCallback: store.updateOrCreateTeacher,
      updateCallback: store.updateOrCreateTeacher,
    });

    await mockPlaywrightCrud<Product, DTOProduct>({
      data: store.products,
      routeUrl: "http://localhost:8071/api/v1.0/admin/products/",
      page,
      createCallback: store.postUpdate,
      updateCallback: store.postUpdate,
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

    const price = page.getByLabel("Price *");
    await price.fill("200");

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
      optionsResult: CONTRACT_DEFINITION_OPTIONS_REQUEST_RESULT,
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
    await page.getByTestId("search-add-button").nth(0).click();
    await expect(
      page.getByRole("heading", { name: "close Add a contract" }),
    ).toBeVisible();
    await page.getByLabel("Title", { exact: true }).click();
    await page.getByLabel("Title", { exact: true }).fill("Test contract");
    await page.getByLabel("Description", { exact: true }).click();
    await page
      .getByLabel("Description", { exact: true })
      .fill("Test contract desc");
    await page.getByLabel("Template name", { exact: true }).click();
    await page
      .getByRole("option", { name: "Contract Definition Default" })
      .click();
    const MdEditorBody = page
      .getByLabel("Add a contract definition")
      .getByTestId("md-editor-body")
      .getByRole("textbox");
    await MdEditorBody.click();
    await MdEditorBody.fill("> Body");
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

    // By default the course is marked as graded
    await expect(
      page.getByRole("checkbox", {
        name: "Taken into account for certification",
      }),
    ).toBeChecked();

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
      .getByRole("row", {
        name: `Select row ${courseRuns[0].course.code} ${courseRuns[0].title}`,
      })
      .getByLabel("Select row")
      .check();
    await page.getByTestId("submit-button-product-target-course-form").click();

    await expect(
      page.getByText("Operation completed successfully."),
    ).toBeVisible();

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
      .getByRole("row", { name: `Unselect row` })
      .getByLabel("Unselect row")
      .uncheck();
    await page.getByTestId("submit-button-product-target-course-form").click();
    await expect(
      page.getByText("Operation completed successfully."),
    ).toBeVisible();
    await expect(
      targetCourseLocator.getByText("All selected course_runs."),
    ).toBeVisible();
  });

  test("Check is graded target course", async ({ page }) => {
    const product = store.products[0];
    product.target_courses = ProductTargetCourseRelationFactory(2);
    product.target_courses[0].is_graded = false;
    await mockPlaywrightCrud<Product, DTOProduct>({
      data: store.products,
      routeUrl: "http://localhost:8071/api/v1.0/admin/products/",
      page,
      createCallback: store.postUpdate,
    });
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

    await expect(
      page
        .getByTestId(
          `item-product-target-course-${product.target_courses[0].course.id}`,
        )
        .getByTestId("SchoolIcon"),
    ).not.toBeVisible();

    await expect(
      page
        .getByTestId(
          `item-product-target-course-${product.target_courses[1].course.id}`,
        )
        .getByTestId("SchoolIcon"),
    ).toBeVisible();

    await page
      .getByTestId(
        `item-product-target-course-${product.target_courses[1].course.id}`,
      )
      .getByTestId("SchoolIcon")
      .hover();

    await delay(210);
    await expect(
      page.getByRole("tooltip", {
        name: "Taken into account for certification",
      }),
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
    await page.getByRole("tab", { name: "Syllabus" }).click();
    await expect(
      page.getByRole("heading", { name: "Relation to courses" }),
    ).toBeVisible();
    await expect(
      page
        .getByRole("alert")
        .getByText(
          "In this section, you have access to all courses to which this product is attached. Click on the course title to navigate to its detail.",
        ),
    ).toBeVisible();
    await expect(
      page.getByRole("button", { name: "Add order group" }).first(),
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
    await page.getByRole("tab", { name: "Syllabus" }).click();

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

  test("Edit certification information", async ({ page }) => {
    const product = store.products[0];
    // Simulate that certification information are empties
    product.certificate_definition = null;
    product.certification_level = null;
    product.teachers = [];
    product.skills = [];

    // Go to the product page
    await page.goto(PATH_ADMIN.products.list);
    await page.getByRole("link", { name: product.title }).click();
    expect(
      await page.getByRole("heading", { name: product.title, level: 4 }),
    ).toBeVisible();

    // Then go to the certification step
    await page.getByRole("button", { name: "Certification" }).click();

    const certificateDefinition = await page.getByLabel(
      "Certificate definition",
    );
    expect(certificateDefinition).toBeVisible();
    expect(certificateDefinition).toHaveValue("");

    // As no certificate definition has been set, other fields should be hidden
    let certificationLevel = await page.getByLabel("Certification level");
    let teachers = await page.getByLabel("Teachers");
    let skills = await page.getByLabel("Skills");

    expect(certificationLevel).not.toBeVisible();
    expect(teachers).not.toBeVisible();
    expect(skills).not.toBeVisible();

    // Set a certificate definition
    await certificateDefinition.click();
    await page
      .getByRole("option", { name: store.certificateDefinitions[1].title })
      .click();

    await expect(
      page.getByText("Operation completed successfully."),
    ).toBeVisible();

    certificationLevel = await page.getByLabel("Certification level");
    teachers = await page.getByLabel("Teachers");
    skills = await page.getByLabel("Skills");
    expect(certificationLevel).toBeVisible();
    expect(teachers).toBeVisible();
    expect(skills).toBeVisible();

    // Now set a certification level
    certificationLevel.fill("0");

    // Then set teachers
    await teachers.click();
    await page
      .getByRole("option", {
        name: `${store.teachers[1].first_name} ${store.teachers[1].last_name}`,
      })
      .click();

    // And finally skills
    await skills.click();
    await page.getByRole("option", { name: store.skills[1].title }).click();

    await expect(
      page.getByText("Operation completed successfully."),
    ).toBeVisible();
    await expect(
      page.getByText(
        "An error occurred while updating the product. Please retry later.",
      ),
    ).not.toBeVisible();
  });

  test("Edit certification information - 1 <= Certification level <= 8", async ({
    page,
  }) => {
    const product = store.products[0];

    // Go to the product page
    await page.goto(PATH_ADMIN.products.list);
    await page.getByRole("link", { name: product.title }).click();
    expect(
      await page.getByRole("heading", { name: product.title, level: 4 }),
    ).toBeVisible();

    // Then go to the certification step
    await page.getByRole("button", { name: "Certification" }).click();

    const certificationLevel = await page.getByLabel("Certification level");
    expect(certificationLevel).toBeVisible();

    await certificationLevel.fill("9");
    await expect(
      page.getByText("certification_level must be less than or equal to 8"),
    ).toBeVisible();

    await certificationLevel.fill("-1");
    await expect(
      page.getByText("certification_level must be greater than or equal to 1"),
    ).toBeVisible();

    // if user types 0, null value should be used
    await certificationLevel.fill("0");
    const request = await page.waitForRequest(
      (req) =>
        req.method() === "PATCH" &&
        req.url().endsWith(`/api/v1.0/admin/products/${product.id}/`),
    );

    const body = request.postDataJSON();
    expect(body.certification_level).toBeNull();
    await expect(
      page.getByText("Operation completed successfully."),
    ).toBeVisible();
  });

  test("Edit certification information - Create teacher", async ({ page }) => {
    const product = store.products[0];

    // Go to the product page
    await page.goto(PATH_ADMIN.products.list);
    await page.getByRole("link", { name: product.title }).click();
    expect(
      await page.getByRole("heading", { name: product.title, level: 4 }),
    ).toBeVisible();

    // Then go to the certification step
    await page.getByRole("button", { name: "Certification" }).click();

    // Then create a new teacher
    const createTeacherButton = await page
      .getByRole("button", {
        name: "Create a resource",
      })
      .first();
    expect(createTeacherButton).toBeVisible();
    await createTeacherButton.click();

    const createModal = await page.getByRole("dialog", { name: "Create" });
    expect(createModal).toBeVisible();
    const firstNameField = await createModal.getByRole("textbox", {
      name: "First name",
    });
    const lastNameField = await createModal.getByRole("textbox", {
      name: "Last name",
    });

    await firstNameField.fill("John");
    await lastNameField.fill("Doe");

    const response = page.waitForResponse(
      (res) => res.request().method() === "POST",
    );
    await createModal.getByRole("button", { name: "Submit" }).click();
    const body = await response.then((res) => res.json());
    expect(body.first_name).toBe("John");
    expect(body.last_name).toBe("Doe");

    await expect(
      page.getByText("Operation completed successfully."),
    ).toBeVisible();

    await expect(page.locator(`[data-id='${body.id}']`)).toBeVisible();
  });

  test("Edit certification information - Edit teacher", async ({ page }) => {
    const product = store.products[0];

    // Go to the product page
    await page.goto(PATH_ADMIN.products.list);
    await page.getByRole("link", { name: product.title }).click();
    expect(
      await page.getByRole("heading", { name: product.title, level: 4 }),
    ).toBeVisible();

    // Then go to the certification step
    await page.getByRole("button", { name: "Certification" }).click();

    // Then edit a current teacher
    const teacher = product.teachers[0];
    const teacherChip = page.locator(`[data-id='${teacher.id}']`);
    await teacherChip.click();

    const createModal = await page.getByRole("dialog", { name: "Edit" });
    expect(createModal).toBeVisible();
    const firstNameField = await createModal.getByRole("textbox", {
      name: "First name",
    });
    const lastNameField = await createModal.getByRole("textbox", {
      name: "Last name",
    });

    expect(await firstNameField.inputValue()).toBe(teacher.first_name);
    expect(await lastNameField.inputValue()).toBe(teacher.last_name);
    await firstNameField.fill("John");
    await lastNameField.fill("Doe");

    const response = page.waitForResponse(
      (res) => res.request().method() === "PATCH",
    );
    await createModal.getByRole("button", { name: "Submit" }).click();
    const body = await response.then((res) => res.json());
    expect(body.first_name).toBe("John");
    expect(body.last_name).toBe("Doe");

    await expect(
      page.getByText("Operation completed successfully."),
    ).toBeVisible();

    await expect(teacherChip).toBeVisible();
    expect(await teacherChip.textContent()).toBe("John Doe");
  });

  test("Edit certification information - Unlink teacher to product", async ({
    page,
  }) => {
    const product = store.products[0];

    // Go to the product page
    await page.goto(PATH_ADMIN.products.list);
    await page.getByRole("link", { name: product.title }).click();
    expect(
      await page.getByRole("heading", { name: product.title, level: 4 }),
    ).toBeVisible();

    // Then go to the certification step
    await page.getByRole("button", { name: "Certification" }).click();

    // Then unlink a teacher
    const [unlinkedTeacher, ...teachers] = product.teachers;
    const teacherChip = page.locator(`[data-id='${unlinkedTeacher.id}']`);
    const deleteTeacherChip = await teacherChip.getByTestId("CancelIcon");
    await deleteTeacherChip.click();

    const request = await page.waitForRequest(
      (req) =>
        req.method() === "PATCH" &&
        req.url().endsWith(`/api/v1.0/admin/products/${product.id}/`),
    );
    const body = request.postDataJSON();
    expect(body.teachers).toEqual(teachers.map(({ id }) => id));

    expect(teacherChip).not.toBeVisible();
  });

  test("Edit certification information - Create skill", async ({ page }) => {
    const product = store.products[0];

    // Go to the product page
    await page.goto(PATH_ADMIN.products.list);
    await page.getByRole("link", { name: product.title }).click();
    expect(
      await page.getByRole("heading", { name: product.title, level: 4 }),
    ).toBeVisible();

    // Then go to the certification step
    await page.getByRole("button", { name: "Certification" }).click();

    // Then create a new skill
    const createSkillButton = await page
      .getByRole("button", {
        name: "Create a resource",
      })
      .nth(1);
    expect(createSkillButton).toBeVisible();
    await createSkillButton.click();

    const createModal = await page.getByRole("dialog", { name: "Create" });
    expect(createModal).toBeVisible();
    const titleField = await createModal.getByRole("textbox", {
      name: "Title",
    });

    await titleField.fill("Javascript");

    const response = page.waitForResponse(
      (res) => res.request().method() === "POST",
    );
    await createModal.getByRole("button", { name: "Submit" }).click();
    const body = await response.then((res) => res.json());
    expect(body.title).toBe("Javascript");

    await expect(
      page.getByText("Operation completed successfully."),
    ).toBeVisible();

    await expect(page.locator(`[data-id='${body.id}']`)).toBeVisible();
  });

  test("Edit certification information - Edit skill", async ({ page }) => {
    const product = store.products[0];

    // Go to the product page
    await page.goto(PATH_ADMIN.products.list);
    await page.getByRole("link", { name: product.title }).click();
    expect(
      await page.getByRole("heading", { name: product.title, level: 4 }),
    ).toBeVisible();

    // Then go to the certification step
    await page.getByRole("button", { name: "Certification" }).click();

    // Then edit a current skill
    const skill = product.skills[0];
    const skillChip = page.locator(`[data-id='${skill.id}']`);
    await skillChip.click();

    const createModal = await page.getByRole("dialog", { name: "Edit" });
    expect(createModal).toBeVisible();
    const titleField = await createModal.getByRole("textbox", {
      name: "Title",
    });

    expect(await titleField.inputValue()).toBe(skill.title);
    await titleField.fill("Python");

    const response = page.waitForResponse(
      (res) => res.request().method() === "PATCH",
    );
    await createModal.getByRole("button", { name: "Submit" }).click();
    const body = await response.then((res) => res.json());
    expect(body.title).toBe("Python");

    await expect(
      page.getByText("Operation completed successfully."),
    ).toBeVisible();

    await expect(skillChip).toBeVisible();
    expect(await skillChip.textContent()).toBe("Python");
  });

  test("Edit certification information - Unlink skill to product", async ({
    page,
  }) => {
    const product = store.products[0];

    // Go to the product page
    await page.goto(PATH_ADMIN.products.list);
    await page.getByRole("link", { name: product.title }).click();
    expect(
      await page.getByRole("heading", { name: product.title, level: 4 }),
    ).toBeVisible();

    // Then go to the certification step
    await page.getByRole("button", { name: "Certification" }).click();

    // Then unlink a skill
    const [unlinkedSkill, ...skills] = product.skills;
    const skillChip = page.locator(`[data-id='${unlinkedSkill.id}']`);
    const deleteSkillChip = await skillChip.getByTestId("CancelIcon");
    await deleteSkillChip.click();

    const request = await page.waitForRequest(
      (req) =>
        req.method() === "PATCH" &&
        req.url().endsWith(`/api/v1.0/admin/products/${product.id}/`),
    );
    const body = request.postDataJSON();
    expect(body.skills).toEqual(skills.map(({ id }) => id));

    expect(skillChip).not.toBeVisible();
  });
});

test.describe("Product form page", () => {
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
  test("Check all form tabs", async ({ page }) => {
    const product = store.products[0];
    await page.goto(PATH_ADMIN.products.list);
    await expect(page.getByRole("heading", { name: "Products" })).toBeVisible();
    await page.getByRole("link", { name: product.title }).click();
    await page.getByRole("tab", { name: "General" }).click();
    await page.getByRole("tab", { name: "Syllabus" }).click();
  });
});
