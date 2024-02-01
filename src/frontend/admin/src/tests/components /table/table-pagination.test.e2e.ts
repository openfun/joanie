import { expect, test } from "@playwright/test";
import { mockPlaywrightCrud } from "@/tests/useResourceHandler";
import { CourseRun, DTOCourseRun } from "@/services/api/models/CourseRun";
import { PATH_ADMIN } from "@/utils/routes/path";
import { getCourseRunTestScenario } from "@/tests/course-run/CourseRunTestScenario";

test.describe("Pagination content", () => {
  test("Check the pagination component with 5 items", async ({ page }) => {
    const store = getCourseRunTestScenario(5);
    await mockPlaywrightCrud<CourseRun, DTOCourseRun>({
      data: store.courseRuns,
      routeUrl: "http://localhost:8071/api/v1.0/admin/course-runs/",
      page,
    });
    await page.goto(PATH_ADMIN.courses_run.list);
    await expect(
      page.getByRole("heading", { name: "Course runs" }),
    ).toBeVisible();
    const paginationLocator = page.getByTestId("table-pagination");
    await expect(paginationLocator).toBeVisible();
    await expect(
      paginationLocator.getByLabel("Go to previous page"),
    ).toBeVisible();
    await expect(
      paginationLocator.getByLabel("Go to previous page"),
    ).toBeDisabled();
    await expect(paginationLocator.getByLabel("page 1")).toBeVisible();
    await expect(paginationLocator.getByLabel("Go to page 2")).toBeHidden();
    await expect(paginationLocator.getByLabel("Go to next page")).toBeVisible();
    await expect(
      paginationLocator.getByLabel("Go to next page"),
    ).toBeDisabled();
  });

  test("Check the pagination component with 25 items", async ({ page }) => {
    const store = getCourseRunTestScenario(25);
    await mockPlaywrightCrud<CourseRun, DTOCourseRun>({
      data: store.courseRuns,
      routeUrl: "http://localhost:8071/api/v1.0/admin/course-runs/",
      page,
    });
    await page.goto(PATH_ADMIN.courses_run.list);
    await expect(
      page.getByRole("heading", { name: "Course runs" }),
    ).toBeVisible();
    const paginationLocator = page.getByTestId("table-pagination");
    await expect(paginationLocator).toBeVisible();
    await expect(
      paginationLocator.getByLabel("Go to previous page"),
    ).toBeVisible();
    await expect(
      paginationLocator.getByLabel("Go to previous page"),
    ).toBeDisabled();
    await expect(paginationLocator.getByLabel("page 1")).toBeVisible();
    await expect(paginationLocator.getByLabel("Go to page 2")).toBeVisible();
    await expect(paginationLocator.getByLabel("Go to page 3")).toBeHidden();
    await expect(paginationLocator.getByLabel("Go to next page")).toBeVisible();
  });
  test("Check the pagination component with 190 items", async ({ page }) => {
    const store = getCourseRunTestScenario(190);
    await mockPlaywrightCrud<CourseRun, DTOCourseRun>({
      data: store.courseRuns,
      routeUrl: "http://localhost:8071/api/v1.0/admin/course-runs/",
      page,
    });
    await page.goto(PATH_ADMIN.courses_run.list);
    await expect(
      page.getByRole("heading", { name: "Course runs" }),
    ).toBeVisible();
    const paginationLocator = page.getByTestId("table-pagination");
    await expect(paginationLocator).toBeVisible();
    await expect(
      paginationLocator.getByLabel("Go to previous page"),
    ).toBeVisible();
    await expect(
      paginationLocator.getByLabel("Go to previous page"),
    ).toBeDisabled();
    await expect(paginationLocator.getByLabel("Go to page 1")).toBeVisible();
    await expect(paginationLocator.getByLabel("Go to page 2")).toBeVisible();
    await expect(paginationLocator.getByLabel("Go to page 3")).toBeVisible();
    await expect(paginationLocator.getByLabel("Go to page 4")).toBeVisible();
    await expect(paginationLocator.getByLabel("Go to page 5")).toBeVisible();
    await expect(paginationLocator.getByText("…")).toBeVisible();
    await expect(paginationLocator.getByLabel("Go to page 10")).toBeVisible();
    await expect(paginationLocator.getByLabel("Go to next page")).toBeVisible();
  });
});

test.describe("Pagination navigation", () => {
  test("Check the pagination component navigation with 70 items", async ({
    page,
  }) => {
    const store = getCourseRunTestScenario(70);
    await mockPlaywrightCrud<CourseRun, DTOCourseRun>({
      data: store.courseRuns,
      routeUrl: "http://localhost:8071/api/v1.0/admin/course-runs/",
      page,
    });
    await page.goto(PATH_ADMIN.courses_run.list);
    await expect(
      page.getByRole("heading", { name: "Course runs" }),
    ).toBeVisible();
    const paginationLocator = page.getByTestId("table-pagination");
    const nextPageLocator = paginationLocator.getByLabel("Go to next page");
    await expect(paginationLocator).toBeVisible();
    await expect(
      paginationLocator.getByRole("button", { name: "1" }),
    ).toHaveAttribute("aria-current");

    const firstPageItems = [...store.courseRuns].splice(0, 20);
    await Promise.all(
      firstPageItems.map(async (courseRun) => {
        const rowLocator = page.locator(`[data-id='${courseRun.id}']`);
        await expect(rowLocator).toBeVisible();
      }),
    );

    // Go to page 2
    await nextPageLocator.click();
    await expect(
      paginationLocator.getByRole("button", { name: "2" }),
    ).toHaveAttribute("aria-current");
    await expect(
      paginationLocator.getByRole("button", { name: "1" }),
    ).not.toHaveAttribute("aria-current");
    const secondPageItems = [...store.courseRuns].splice(20, 20);
    await Promise.all(
      secondPageItems.map(async (courseRun) => {
        const rowLocator = page.locator(`[data-id='${courseRun.id}']`);
        await expect(rowLocator).toBeVisible();
      }),
    );
    await Promise.all(
      firstPageItems.map(async (courseRun) => {
        const rowLocator = page.locator(`[data-id='${courseRun.id}']`);
        await expect(rowLocator).toBeHidden();
      }),
    );

    // Go to page 4
    await paginationLocator.getByLabel("Go to page 4").click();
    await expect(
      paginationLocator.getByRole("button", { name: "4" }),
    ).toHaveAttribute("aria-current");
    await expect(
      paginationLocator.getByRole("button", { name: "2" }),
    ).not.toHaveAttribute("aria-current");
  });
});
