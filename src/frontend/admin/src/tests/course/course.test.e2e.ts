import { expect, test } from "@playwright/test";
import { PATH_ADMIN } from "@/utils/routes/path";
import { getCourseScenarioStore } from "@/tests/course/CourseTestScenario";
import { mockPlaywrightCrud } from "@/tests/useResourceHandler";
import { Course, DTOCourse } from "@/services/api/models/Course";
import { COURSE_OPTIONS_REQUEST_RESULT } from "@/tests/mocks/courses/course-mocks";
import {
  DTOOrganization,
  Organization,
} from "@/services/api/models/Organization";
import { ORGANIZATION_OPTIONS_REQUEST_RESULT } from "@/tests/mocks/organizations/organization-mock";
import { DTOProduct, Product } from "@/services/api/models/Product";
import { expectHaveClasses } from "@/tests/utils";
import { User } from "@/services/api/models/User";
import { CourseRun, DTOCourseRun } from "@/services/api/models/CourseRun";

const coursesApiUrl = "http://localhost:8071/api/v1.0/admin/courses/";
test.describe("Course form", async () => {
  let store = getCourseScenarioStore();
  test.beforeEach(async ({ page }) => {
    store = getCourseScenarioStore();
    await mockPlaywrightCrud<User, any>({
      data: store.users,
      routeUrl: "http://localhost:8071/api/v1.0/admin/users/",
      page,
    });

    await mockPlaywrightCrud<CourseRun, DTOCourseRun>({
      data: store.courseRuns,
      routeUrl: "http://localhost:8071/api/v1.0/admin/course-runs/",
      page,
    });

    await mockPlaywrightCrud<Product, DTOProduct>({
      data: store.products,
      routeUrl: "http://localhost:8071/api/v1.0/admin/products/",
      page,
    });

    await mockPlaywrightCrud<Organization, DTOOrganization>({
      data: store.organizations,
      routeUrl: "http://localhost:8071/api/v1.0/admin/organizations/",
      page,
      createCallback: store.createOrg,
      optionsResult: ORGANIZATION_OPTIONS_REQUEST_RESULT,
    });

    await mockPlaywrightCrud<Course, DTOCourse>({
      data: store.list,
      routeUrl: coursesApiUrl,
      page,
      createCallback: store.postUpdate,
      updateCallback: store.postUpdate,
      searchResult: store.list[1],
      optionsResult: COURSE_OPTIONS_REQUEST_RESULT,
    });
  });

  test("Check that the form is complete and contains the necessary", async ({
    page,
  }) => {
    await page.goto(PATH_ADMIN.courses.list);

    await page.getByRole("button", { name: "Add" }).click();
    await expect(
      page.getByRole("heading", { name: "Add a course" }),
    ).toBeVisible();

    await expect(
      page.getByRole("heading", { name: "Main information" }),
    ).toBeVisible();
    await expect(page.getByLabel("Title")).toBeVisible();
    await expect(page.getByLabel("Code")).toBeVisible();
    await expect(page.getByLabel("Effort")).toBeVisible();
    await expect(
      page.getByText("The estimated duration in hours to fulfill the course"),
    ).toBeVisible();

    await expect(page.getByLabel("Organizations")).toBeVisible();
    await page.getByTestId("search-add-button").click();
    await page
      .getByRole("heading", { name: "close Add an organization" })
      .click();
  });

  test("Create a new course ", async ({ page }) => {
    await store.mockCourseRunsFromCourse(page, []);

    await page.goto(PATH_ADMIN.courses.list);
    await page.getByRole("button", { name: "Add" }).click();
    await expect(
      page.getByRole("heading", { name: "Add a course" }),
    ).toBeVisible();

    await page.getByLabel("Title").click();
    await page.getByLabel("Title").fill("Test course");
    await page.getByLabel("Code", { exact: true }).click();
    await page.getByLabel("Code", { exact: true }).fill("Test_Course_Code");
    await page.getByLabel("Effort").click();
    await page.getByLabel("Effort").fill("30");
    await page.getByLabel("Organizations").click();
    await page
      .getByRole("option", { name: store.organizations[0].title })
      .click();
    await page.getByLabel("Organizations").click();
    await page
      .getByRole("option", { name: store.organizations[1].title })
      .click();
    await expect(
      page.getByRole("button", { name: store.organizations[0].title }),
    ).toBeVisible();
    await expect(
      page.getByRole("button", { name: store.organizations[1].title }),
    ).toBeVisible();

    await page.getByTestId("search-add-button").click();
    await page
      .getByRole("heading", { name: "close Add an organization" })
      .click();
    await page.getByRole("textbox", { name: "Title" }).click();
    await page.getByRole("textbox", { name: "Title" }).fill("Org title");
    await page.getByRole("textbox", { name: "Code", exact: true }).click();
    await page
      .getByRole("textbox", { name: "Code", exact: true })
      .fill("Org code");
    await page.getByLabel("Representative", { exact: true }).click();
    await page
      .getByLabel("Representative", { exact: true })
      .fill("john.doe@yoppmail.com");
    await page.getByTestId("submit-button-organization-form").click();
    await page.getByText("Operation completed successfully.").click();
    await expect(page.getByRole("button", { name: "Org title" })).toBeVisible();
    await expect(
      page.getByRole("button", { name: store.organizations[0].title }),
    ).toBeVisible();

    await page.getByRole("button", { name: "Submit" }).click();
    await expect(
      page.getByText("Operation completed successfully."),
    ).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Edit course: Test course" }),
    ).toBeVisible();
    await page.getByRole("link", { name: "List" }).click();
    await expect(page.getByRole("heading", { name: "Courses" })).toBeVisible();
    await page.getByRole("gridcell", { name: "Test course" }).click();
    await page.getByRole("gridcell", { name: "TEST_COURSE_CODE" }).click();
  });

  test("Validate an empty form and check error messages", async ({ page }) => {
    await page.goto(PATH_ADMIN.courses.list);
    await page.getByRole("button", { name: "Add" }).click();
    await page.getByRole("button", { name: "Submit" }).click();

    await expectHaveClasses(
      page.getByText("title is a required field"),
      "Mui-error",
    );
    await expectHaveClasses(
      page.getByText("code is a required field"),
      "Mui-error",
    );
    await expectHaveClasses(
      page.getByText("organizations field must have at least 1 items"),
      "Mui-error",
    );

    await page.getByLabel("Title").click();
    await page.getByLabel("Title").fill("Test course");
    await expect(page.getByText("title is a required field")).toHaveCount(0);
    await page.getByLabel("Code", { exact: true }).click();
    await page.getByLabel("Code", { exact: true }).fill("fd");
    await expect(page.getByText("code is a required field")).toHaveCount(0);
    await page.getByLabel("Organizations").click();
    await page
      .getByRole("option", { name: store.organizations[0].title })
      .click();
    await expect(
      page.getByText("organizations field must have at least 1 items"),
    ).toHaveCount(0);
  });

  test("Edit a course", async ({ page }) => {
    const courseToEdit = store.list[0];
    await store.mockCourseRunsFromCourse(page, courseToEdit.courses_runs ?? []);

    await page.goto(PATH_ADMIN.courses.list);
    const oldCourseTitle = courseToEdit.title;
    const newCourseTitle = courseToEdit.title + " update";
    await page.getByRole("link", { name: oldCourseTitle }).click();

    await expect(
      page.getByRole("heading", { name: `Edit course: ${oldCourseTitle}` }),
    ).toBeVisible();

    await page.getByRole("textbox", { name: "Title", exact: true }).click();
    await page
      .getByRole("textbox", { name: "Title", exact: true })
      .fill(newCourseTitle);
    await page.getByRole("button", { name: "Submit" }).click();
    await page.getByText("Operation completed successfully.").click();
    await expect(
      page.getByRole("heading", { name: `Edit course: ${newCourseTitle}` }),
    ).toBeVisible();
    await page.getByRole("link", { name: "List", exact: true }).click();
    await expect(
      page.getByRole("gridcell", { name: oldCourseTitle, exact: true }),
    ).toHaveCount(0);
    await expect(
      page.getByRole("gridcell", { name: newCourseTitle }),
    ).toHaveCount(1);
  });

  test("Click on an course in the list and use it as a template from its form", async ({
    page,
  }) => {
    const courseUsedAsTemplate = store.list[0];
    await store.mockCourseRunsFromCourse(
      page,
      courseUsedAsTemplate.courses_runs ?? [],
    );

    await page.goto(PATH_ADMIN.courses.list);
    await page.getByRole("link", { name: courseUsedAsTemplate.title }).click();
    await page.getByRole("link", { name: "Use as a template" }).click();
    await expect(
      page.getByRole("heading", { name: "Add a course" }),
    ).toBeVisible();
    await expect(page.getByLabel("Title")).toHaveValue(
      courseUsedAsTemplate.title,
    );
    await expect(page.getByLabel("Code")).toHaveValue(
      courseUsedAsTemplate.code,
    );
    await page.getByLabel("Code").click();
    await Promise.all(
      courseUsedAsTemplate.organizations.map(async (org) => {
        await expect(
          page.getByRole("button", { name: org.title }),
        ).toBeVisible();
      }),
    );
  });
});

test.describe("Course list", async () => {
  let store = getCourseScenarioStore();
  test.beforeEach(async ({ page }) => {
    store = getCourseScenarioStore();
    await mockPlaywrightCrud<Course, DTOCourse>({
      data: store.list,
      routeUrl: coursesApiUrl,
      page,
      createCallback: store.postUpdate,
      updateCallback: store.postUpdate,
      searchResult: store.list[1],
      optionsResult: COURSE_OPTIONS_REQUEST_RESULT,
    });
  });

  test("verify all courses are inside the list", async ({ page }) => {
    // Go to the page
    await page.goto(PATH_ADMIN.courses.list);
    await expect(page.getByRole("heading", { name: "Courses" })).toBeVisible();
    await Promise.all(
      store.list.map(async (course) => {
        await expect(page.getByText(course.title)).toBeVisible();
        await expect(page.getByText(course.code)).toBeVisible();
      }),
    );
  });

  test("Search a course in list with the search input", async ({ page }) => {
    // Go to the page
    await mockPlaywrightCrud<Course, DTOCourse>({
      data: store.list,
      routeUrl: coursesApiUrl,
      page,
      createCallback: store.postUpdate,
      searchTimeout: 100,
      updateCallback: store.postUpdate,
      searchResult: store.list[1],
      optionsResult: COURSE_OPTIONS_REQUEST_RESULT,
    });
    await page.goto(PATH_ADMIN.courses.list);
    await expect(page.getByRole("heading", { name: "Courses" })).toBeVisible();
    await Promise.all(
      store.list.map(async (course) => {
        await expect(page.getByText(course.title)).toBeVisible();
        await expect(page.getByText(course.code)).toBeVisible();
      }),
    );
    const searchPlaceholder = "Search by title or code";
    await page.getByPlaceholder(searchPlaceholder).click();
    await page.getByPlaceholder(searchPlaceholder).fill(store.list[1].title);
    await expect(page.getByTestId("circular-loader-container")).toBeVisible();
    await expect(page.getByTestId("circular-loader-container")).toBeHidden();
    await expect(page.getByText(store.list[1].title)).toBeVisible();
    await expect(page.getByText(store.list[0].title)).toBeHidden();
    await page.getByPlaceholder(searchPlaceholder).click();
    await page.getByPlaceholder(searchPlaceholder).fill("");
    await expect(page.getByTestId("circular-loader-container")).toBeVisible();
    await expect(page.getByTestId("circular-loader-container")).toBeHidden();
    await Promise.all(
      store.list.map(async (course) => {
        await expect(page.getByText(course.title)).toBeVisible();
        await expect(page.getByText(course.code)).toBeVisible();
      }),
    );
  });
});

test.describe("Course form page", () => {
  let store = getCourseScenarioStore();
  test.beforeEach(async ({ page }) => {
    store = getCourseScenarioStore();
    await mockPlaywrightCrud<Course, DTOCourse>({
      data: store.list,
      routeUrl: coursesApiUrl,
      page,
      createCallback: store.postUpdate,
      updateCallback: store.postUpdate,
      searchResult: store.list[1],
      optionsResult: COURSE_OPTIONS_REQUEST_RESULT,
    });
  });
  test("Check all form tabs", async ({ page }) => {
    const course = store.list[0];
    await page.goto(PATH_ADMIN.courses.list);
    await expect(page.getByRole("heading", { name: "Courses" })).toBeVisible();
    await page.getByRole("link", { name: course.title }).click();
    await page.getByRole("tab", { name: "General" }).click();
    await page.getByRole("tab", { name: "Members" }).click();
    await page.getByRole("tab", { name: "Course runs" }).click();
    await page.getByRole("tab", { name: "Products" }).click();
  });
});
