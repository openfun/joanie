import { expect, test } from "@playwright/test";
import { mockPlaywrightCrud } from "@/tests/useResourceHandler";
import { Course, DTOCourse } from "@/services/api/models/Course";
import { COURSE_OPTIONS_REQUEST_RESULT } from "@/tests/mocks/courses/course-mocks";
import { CourseRun, DTOCourseRun } from "@/services/api/models/CourseRun";
import { PATH_ADMIN } from "@/utils/routes/path";
import { getCourseRunTestScenario } from "@/tests/course-run/CourseRunTestScenario";
import { findWithClasses } from "@/tests/utils";

const coursesApiUrl = "http://localhost:8071/api/v1.0/admin/courses/";
test.describe("Course run list", () => {
  let store = getCourseRunTestScenario();
  test.beforeEach(async ({ page }) => {
    store = getCourseRunTestScenario();
    const firstCourseRun = store.courseRuns[0];
    firstCourseRun.start = new Date(
      Date.UTC(2024, 1, 23, 7, 30),
    ).toLocaleString();
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

  test("Check if all column are presents", async ({ page }) => {
    await page.goto(PATH_ADMIN.courses_run.list);
    await findWithClasses(
      page.getByText("Title"),
      "MuiDataGrid-columnHeaderTitle",
    );
    await findWithClasses(
      page.getByText("Course code"),
      "MuiDataGrid-columnHeaderTitle",
    );
    await findWithClasses(
      page.getByText("Course start"),
      "MuiDataGrid-columnHeaderTitle",
    );
    await findWithClasses(
      page.getByText("Course end"),
      "MuiDataGrid-columnHeaderTitle",
    );
    await findWithClasses(
      page.getByText("State"),
      "MuiDataGrid-columnHeaderTitle",
    );
  });

  test("Check if all more options are presents", async ({ page }) => {
    const courseRun = store.courseRuns[0];
    await page.goto(PATH_ADMIN.courses_run.list);
    await page
      .getByRole("row", {
        name: `${courseRun.course.code} ${courseRun.title} 2/23/24, 7:30 AM`,
      })
      .getByRole("button")
      .click();

    await expect(page.getByTestId("EditIcon")).toBeVisible();
    await expect(page.getByRole("menuitem", { name: "Edit" })).toBeVisible();
    await expect(
      page.getByRole("menuitem", { name: "Copy url" }),
    ).toBeVisible();
    await expect(
      page.getByRole("menuitem", { name: "Copy the resource link" }),
    ).toBeVisible();
    await expect(
      page.getByRole("menuitem", { name: "Use as a template" }),
    ).toBeVisible();
    await expect(page.getByRole("menuitem", { name: "Delete" })).toBeVisible();
  });

  test("if code and title are links", async ({ page }) => {
    await page.goto(PATH_ADMIN.courses_run.list);
    await Promise.all(
      store.courseRuns.map(async (courseRun) => {
        await expect(
          page.getByRole("link", { name: courseRun.course.code }).first(),
        ).toBeVisible();
        await expect(
          page.getByRole("link", { name: courseRun.title }).first(),
        ).toBeVisible();
      }),
    );
  });
});
