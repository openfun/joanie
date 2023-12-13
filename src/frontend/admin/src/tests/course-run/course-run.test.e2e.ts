import { expect, test } from "@playwright/test";
import {
  getUrlCatchSearchParamsRegex,
  mockPlaywrightCrud,
} from "@/tests/useResourceHandler";
import { Course, DTOCourse } from "@/services/api/models/Course";
import { COURSE_OPTIONS_REQUEST_RESULT } from "@/tests/mocks/courses/course-mocks";
import { CourseRun, DTOCourseRun } from "@/services/api/models/CourseRun";
import { PATH_ADMIN } from "@/utils/routes/path";
import { getCourseRunTestScenario } from "@/tests/course-run/CourseRunTestScenario";
import { expectHaveClasses } from "@/tests/utils";

const coursesApiUrl = "http://localhost:8071/api/v1.0/admin/courses/";
test.describe("Course run form", () => {
  let store = getCourseRunTestScenario();
  //
  test.beforeEach(async ({ page }) => {
    store = getCourseRunTestScenario();

    await mockPlaywrightCrud<CourseRun, DTOCourseRun>({
      data: store.courseRuns,
      routeUrl: "http://localhost:8071/api/v1.0/admin/course-runs/",
      createCallback: store.editOrCreate,
      updateCallback: store.editOrCreate,
      page,
    });

    await mockPlaywrightCrud<Course, DTOCourse>({
      data: store.courses,
      routeUrl: coursesApiUrl,
      searchResult: store.courses[0],
      page,
      optionsResult: COURSE_OPTIONS_REQUEST_RESULT,
    });
  });

  test("Check if all element are present for create mode", async ({ page }) => {
    await page.goto(PATH_ADMIN.courses_run.list);
    await page.getByRole("button", { name: "Add" }).click();
    await expect(page.getByRole("heading", { name: "General" })).toBeVisible();
    const courseRunSearchLocator = page.getByTestId("course-runs-search");
    await expect(courseRunSearchLocator).toBeVisible();
    await expect(
      courseRunSearchLocator.getByTestId("search-add-button"),
    ).toBeVisible();
    // When we arrive in form, nothing is selected, so the edit course mode is disabled
    await expect(
      courseRunSearchLocator.getByTestId("search-edit-button"),
    ).toHaveCount(0);

    await expect(page.getByLabel("Title")).toBeVisible();
    await expect(page.getByLabel("Resource link")).toBeVisible();
    await expect(page.getByLabel("Language")).toBeVisible();
    await expect(page.getByLabel("Start", { exact: true })).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Course run dates" }),
    ).toBeVisible();
    await expect(
      page
        .locator("div")
        .filter({ hasText: /^Start$/ })
        .getByLabel("Choose date"),
    ).toBeVisible();
    await expect(page.getByLabel("End", { exact: true })).toBeVisible();
    await expect(
      page
        .locator("div")
        .filter({ hasText: /^End$/ })
        .getByLabel("Choose date"),
    ).toBeVisible();

    await expect(
      page.getByRole("heading", { name: "Enrollment dates" }),
    ).toBeVisible();
    await expect(page.getByLabel("Enrollment start")).toBeVisible();
    await expect(
      page
        .locator("div")
        .filter({ hasText: /^Enrollment start$/ })
        .getByLabel("Choose date"),
    ).toBeVisible();
    await expect(page.getByLabel("Enrollment end")).toBeVisible();
    await expect(
      page
        .locator("div")
        .filter({ hasText: /^Enrollment end$/ })
        .getByLabel("Choose date"),
    ).toBeVisible();
    await expect(page.getByLabel("Is gradable?")).toBeVisible();
    await expect(page.getByText("Is gradable?")).toBeVisible();
    await expect(page.getByLabel("Is listed?")).toBeVisible();
    await expect(page.getByText("Is listed?")).toBeVisible();
    await expect(
      page.getByText(
        "If checked, the course run can be taken into account for the grading.",
      ),
    ).toBeVisible();
    await expect(
      page.getByText(
        "If checked the course run will be included in the list of course runs available for enrollment on the related course page.",
      ),
    ).toBeVisible();
  });

  test("Submit empty form and check error messages", async ({ page }) => {
    await page.goto(PATH_ADMIN.courses_run.list);
    await page.getByRole("button", { name: "Add" }).click();
    await page.getByTestId("submit-button-course-run-form").click();
    await expectHaveClasses(
      page.getByText("course is a required field"),
      "Mui-error",
    );
    await expectHaveClasses(
      page.getByText("title is a required field"),
      "Mui-error",
    );
    await expectHaveClasses(
      page.getByText("resource_link is a required"),
      "Mui-error",
    );
  });

  test("Submit a course_run with a resource_link already in use.", async ({
    page,
  }) => {
    const courseRun = store.courseRuns[0];
    await page.goto(PATH_ADMIN.courses_run.list);
    await page
      .getByRole("row", { name: courseRun.title })
      .getByRole("button")
      .click();
    await page.getByRole("menuitem", { name: "Use as a template" }).click();
    const urlRegex = getUrlCatchSearchParamsRegex(
      "http://localhost:8071/api/v1.0/admin/course-runs/",
    );
    await page.unroute(urlRegex);
    await page.route(urlRegex, async (route, request) => {
      const methods = request.method();

      if (methods === "POST") {
        await route.fulfill({
          status: 400,
          json: {
            resource_link: [
              "A Course Session object with this resource link field already exists.",
            ],
          },
        });
      }
    });

    await page.getByTestId("submit-button-course-run-form").click();
    await expect(
      page.getByText(
        "An error occurred while creating the course-run. Please retry later.",
      ),
    ).toBeVisible();
    await expectHaveClasses(
      page.getByText(
        "A Course Session object with this resource link field already exists.",
      ),
      "Mui-error",
    );
  });

  test("Create new course run", async ({ page }) => {
    const course = store.courses[0];
    await page.goto(PATH_ADMIN.courses_run.list);
    await page.getByRole("button", { name: "Add" }).click();
    await expect(
      page.getByRole("heading", { name: "Add a course run" }),
    ).toBeVisible();

    await page.getByLabel("Course").click();
    await page.getByLabel("Course").fill(course.title);
    await page.getByRole("option", { name: course.title }).click();
    await page.getByLabel("Title").click();
    await page.getByLabel("Title").fill("Course run title");
    await page.getByLabel("Resource link").click();
    await page.getByLabel("Resource link").fill("http://localhost:8072/");
    await page.getByLabel("Language").click();
    await page.getByRole("option", { name: "Français" }).click();
    await page.getByLabel("Start", { exact: true }).click();
    await page
      .locator("div")
      .filter({ hasText: /^Start$/ })
      .getByLabel("Choose date")
      .click();
    await page.getByRole("gridcell", { name: "11" }).first().click();
    await page.getByRole("button", { name: "OK" }).click();
    await page.getByLabel("End", { exact: true }).click();
    await page
      .locator("div")
      .filter({ hasText: /^End$/ })
      .getByLabel("Choose date")
      .click();
    await page.getByRole("gridcell", { name: "27" }).nth(1).click();
    await page.getByRole("button", { name: "OK" }).click();
    await page.getByLabel("Enrollment start").click();
    await page
      .locator("div")
      .filter({ hasText: /^Enrollment start$/ })
      .getByLabel("Choose date")
      .click();
    await page.getByRole("gridcell", { name: "1", exact: true }).nth(1).click();
    await page.getByRole("button", { name: "OK" }).click();
    await page
      .locator("div")
      .filter({ hasText: /^Enrollment end$/ })
      .getByLabel("Choose date")
      .click();
    await page.getByRole("gridcell", { name: "10" }).nth(1).click();
    await page.getByRole("button", { name: "OK" }).click();
    await page.getByTestId("submit-button-course-run-form").click();
    await page.getByText("Operation completed successfully.").click();
    await expect(
      page.getByRole("heading", { name: "Edit course run: Course run" }),
    ).toBeVisible();
    await page.getByRole("link", { name: "List" }).click();
    await expect(
      page.getByRole("cell", { name: "Course run title" }),
    ).toBeVisible();
  });
});
