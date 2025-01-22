import { Page } from "@playwright/test";
import { CourseRun } from "@/services/api/models/CourseRun";
import { catchAllIdRegex } from "@/tests/useResourceHandler";

export const mockCourseRunsFromCourse = async (
  page: Page,
  courseRuns: CourseRun[],
) => {
  const courseRunFromCourseRegex = catchAllIdRegex(
    "http://localhost:8071/api/v1.0/admin/courses/:uuid/course-runs/",
    ":uuid",
  );
  await page.unroute(courseRunFromCourseRegex);
  await page.route(courseRunFromCourseRegex, async (route, request) => {
    const methods = request.method();
    if (methods === "GET") {
      await route.fulfill({ json: courseRuns });
    }
  });
};
