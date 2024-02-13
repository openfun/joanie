import { expect, test } from "@playwright/test";
import { mockPlaywrightCrud } from "@/tests/useResourceHandler";
import { PATH_ADMIN } from "@/utils/routes/path";
import { getCourseScenarioStore } from "@/tests/course/CourseTestScenario";
import { Course, DTOCourse } from "@/services/api/models/Course";
import { COURSE_OPTIONS_REQUEST_RESULT } from "@/tests/mocks/courses/course-mocks";
import {
  DTOOrganization,
  Organization,
} from "@/services/api/models/Organization";

const coursesApiUrl = "http://localhost:8071/api/v1.0/admin/courses/";
test.describe("Course filters", () => {
  let store = getCourseScenarioStore();

  test.beforeEach(async ({ page }) => {
    store = getCourseScenarioStore();
    await mockPlaywrightCrud<Course, DTOCourse>({
      data: store.list,
      routeUrl: coursesApiUrl,
      page,
      optionsResult: COURSE_OPTIONS_REQUEST_RESULT,
    });
    await mockPlaywrightCrud<Organization, DTOOrganization>({
      data: store.organizations,
      routeUrl: "http://localhost:8071/api/v1.0/admin/organizations/",
      page,
    });
  });

  test("Check the presence and proper functioning of the filters", async ({
    page,
  }) => {
    await page.goto(PATH_ADMIN.courses.list);
    await expect(page.getByRole("heading", { name: "Courses" })).toBeVisible();

    // Check all certificate definition
    await Promise.all(
      store.list.map(async (course) => {
        await expect(
          page.getByRole("link", { name: course.title }),
        ).toBeVisible();
      }),
    );

    // Check if all filters are presents
    await expect(
      page.getByPlaceholder("Search by title or code"),
    ).toBeVisible();
    await page.getByRole("button", { name: "Filters" }).click();
    await expect(page.getByRole("heading", { name: "filters" })).toBeVisible();

    const selectOrgSelector = page.getByLabel("Organizations");
    await expect(selectOrgSelector).toBeVisible();
    await selectOrgSelector.click();

    // Check filters result
    const filterResult = [store.list[1], store.list[2]];
    await mockPlaywrightCrud<Course, DTOCourse>({
      data: store.list,
      routeUrl: coursesApiUrl,
      page,
      forceFiltersMode: true,
      searchResult: filterResult,
      optionsResult: COURSE_OPTIONS_REQUEST_RESULT,
    });

    await page
      .getByRole("option", { name: store.organizations[0].title })
      .click();

    await page.getByLabel("close").click();

    await Promise.all(
      filterResult.map(async (course) => {
        await expect(
          page.getByRole("link", { name: course.title }),
        ).toBeVisible();
      }),
    );

    // Check that the list returns to the initial state
    await mockPlaywrightCrud<Course, DTOCourse>({
      data: store.list,
      routeUrl: coursesApiUrl,
      page,
      searchResult: filterResult,
      forceFiltersMode: false,
      optionsResult: COURSE_OPTIONS_REQUEST_RESULT,
    });

    // Remove all filters
    await page.getByRole("button", { name: "Clear" }).click();
    await Promise.all(
      store.list.map(async (certificate) => {
        await expect(
          page.getByRole("link", { name: certificate.title }),
        ).toBeVisible();
      }),
    );
  });
});
