import { expect, test } from "@playwright/test";
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
import { User } from "@/services/api/models/User";
import { CourseRun, DTOCourseRun } from "@/services/api/models/CourseRun";
import { PATH_ADMIN } from "@/utils/routes/path";

const coursesApiUrl = "http://localhost:8071/api/v1.0/admin/courses/";
test.describe("Course product relation", () => {
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

  test("Check if current course is selected", async ({ page }) => {
    const course = store.list[0];
    await page.goto(PATH_ADMIN.courses.list);
    await store.mockCourseRunsFromCourse(page, []);
    await page.getByRole("link", { name: course.title }).click();

    await page.getByRole("button", { name: "Add a course run" }).click();
    await expect(page.getByRole("textbox", { name: "Title" })).toBeVisible();
    await expect(page.getByLabel("Course", { exact: true })).toBeDisabled();
    await expect(page.getByLabel("Course", { exact: true })).toHaveValue(
      course.title,
    );
  });
  test("Copy url inside the clipboard", async ({ page, context }) => {
    await context.grantPermissions(["clipboard-read", "clipboard-write"]);
    const course = store.list[0];
    const courseRun = course.courses_runs![0];
    await page.goto(PATH_ADMIN.courses.list);
    await store.mockCourseRunsFromCourse(page, course.courses_runs ?? []);
    await page.getByRole("link", { name: course.title }).click();
    await expect(
      page.getByRole("heading", { name: `Edit course: ${course.title}` }),
    ).toBeVisible();

    await page
      .getByRole("row", { name: `${courseRun.title} Click to copy` })
      .getByRole("button")
      .click();
    await page.getByRole("menuitem", { name: "Copy url" }).click();
    await expect(
      page.getByRole("alert").getByText("Link added to your clipboard"),
    ).toBeVisible();
    const handle = await page.evaluateHandle(() =>
      navigator.clipboard.readText(),
    );
    const clipboardContent = await handle.jsonValue();
    expect(clipboardContent).toEqual(courseRun.uri);
  });
});
