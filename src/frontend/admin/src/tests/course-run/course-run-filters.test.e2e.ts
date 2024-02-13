import { expect, test } from "@playwright/test";
import { mockPlaywrightCrud } from "@/tests/useResourceHandler";
import { Course, DTOCourse } from "@/services/api/models/Course";
import { PATH_ADMIN } from "@/utils/routes/path";
import { getCourseRunTestScenario } from "@/tests/course-run/CourseRunTestScenario";
import { CourseRun, DTOCourseRun } from "@/services/api/models/CourseRun";
import { COURSE_OPTIONS_REQUEST_RESULT } from "@/tests/mocks/courses/course-mocks";

test.describe("Course run filters", () => {
  let store = getCourseRunTestScenario();
  //
  test.beforeEach(async ({ page }) => {
    store = getCourseRunTestScenario();

    await mockPlaywrightCrud<CourseRun, DTOCourseRun>({
      data: store.courseRuns,
      routeUrl: "http://localhost:8071/api/v1.0/admin/course-runs/",
      page,
    });
  });

  test("Check if all filters are presents", async ({ page }) => {
    await page.goto(PATH_ADMIN.courses_run.list);
    // Wait the page
    await expect(
      page.getByRole("heading", { name: "Course runs" }),
    ).toBeVisible();

    // Click on filters button
    await page.getByRole("button", { name: "Filters" }).click();

    // Check the course and state inputs
    await expect(
      page.getByTestId("course-runs-search").getByLabel("Course"),
    ).toBeVisible();
    await expect(
      page.getByTestId("select-course-run-state").getByLabel("State"),
    ).toBeVisible();

    // Check the is listed radio buttons
    await expect(page.getByText("Is listed?")).toBeVisible();
    await expect(
      page.getByTestId("course-run-isListed-filter").getByLabel("None"),
    ).toBeVisible();
    await expect(
      page.getByTestId("course-run-isListed-filter").getByLabel("Yes"),
    ).toBeVisible();
    await expect(
      page
        .getByTestId("course-run-isListed-filter")
        .getByLabel("No", { exact: true }),
    ).toBeVisible();
    await expect(
      page.getByTestId("course-run-isListed-filter").getByText("None"),
    ).toBeVisible();
    await expect(
      page.getByTestId("course-run-isListed-filter").getByText("Yes"),
    ).toBeVisible();
    await expect(
      page
        .getByTestId("course-run-isListed-filter")
        .getByText("No", { exact: true }),
    ).toBeVisible();

    // Check the is gradable radio buttons
    await expect(page.getByText("Is gradable?")).toBeVisible();
    await expect(
      page.getByTestId("course-run-isGradable-filter").getByLabel("None"),
    ).toBeVisible();
    await expect(
      page.getByTestId("course-run-isGradable-filter").getByText("None"),
    ).toBeVisible();
    await expect(
      page.getByTestId("course-run-isGradable-filter").getByLabel("Yes"),
    ).toBeVisible();
    await expect(
      page.getByTestId("course-run-isGradable-filter").getByText("Yes"),
    ).toBeVisible();
    await expect(
      page
        .getByTestId("course-run-isGradable-filter")
        .getByLabel("No", { exact: true }),
    ).toBeVisible();
    await expect(
      page
        .getByTestId("course-run-isGradable-filter")
        .getByText("No", { exact: true }),
    ).toBeVisible();
  });

  test("Check all chips by filters", async ({ page }) => {
    await mockPlaywrightCrud<Course, DTOCourse>({
      data: store.courses,
      routeUrl: "http://localhost:8071/api/v1.0/admin/courses/",
      searchResult: store.courses[0],
      page,
      optionsResult: COURSE_OPTIONS_REQUEST_RESULT,
    });
    await page.goto(PATH_ADMIN.courses_run.list);
    // Wait the page
    await expect(
      page.getByRole("heading", { name: "Course runs" }),
    ).toBeVisible();

    await page.getByRole("button", { name: "Filters" }).click();
    await page.getByTestId("course-runs-search").getByLabel("Course").click();
    await page.getByTestId("course-runs-search").getByLabel("Course").fill("c");
    await page.getByRole("option", { name: store.courses[0].title }).click();
    await page
      .getByTestId("select-course-run-state")
      .getByLabel("State")
      .click();
    await page.getByRole("option", { name: "Future open" }).click();
    await page
      .getByTestId("course-run-isListed-filter")
      .getByLabel("No", { exact: true })
      .check();
    await page
      .getByTestId("course-run-isGradable-filter")
      .getByLabel("Yes")
      .check();
    await page.getByLabel("close").click();
    await expect(
      page.getByRole("button", { name: `Course: ${store.courses[0].title}` }),
    ).toBeVisible();
    await expect(
      page.getByRole("button", { name: "State: Future open" }),
    ).toBeVisible();
    await expect(
      page.getByRole("button", { name: "Is listed?: No" }),
    ).toBeVisible();
    await expect(
      page.getByRole("button", { name: "Is gradable?: Yes" }),
    ).toBeVisible();
  });
});
