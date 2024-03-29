import { Page } from "@playwright/test";
import { User } from "@/services/api/models/User";
import { EnrollmentFactory } from "@/services/factories/enrollments";
import { CourseRun, DTOCourseRun } from "@/services/api/models/CourseRun";
import {
  getUrlCatchIdRegex,
  getUrlCatchSearchParamsRegex,
  mockPlaywrightCrud,
} from "@/tests/useResourceHandler";
import { transformEnrollmentsToEnrollmentListItems } from "@/services/api/models/Enrollment";

export const getEnrollmentsScenarioStore = (itemsNumber: number = 30) => {
  const list = EnrollmentFactory(itemsNumber);
  const courseRuns: CourseRun[] = [];
  const users: User[] = [];

  list.forEach((enrollment) => {
    courseRuns.push(enrollment.course_run);
    users.push(enrollment.user);
  });

  return {
    list,
    users,
    courseRuns,
  };
};

export const mockAllEnrollmentsEntities = async (
  store: ReturnType<typeof getEnrollmentsScenarioStore>,
  page: Page,
) => {
  const url = "http://localhost:8071/api/v1.0/admin/enrollments/";
  const catchIdRegex = getUrlCatchIdRegex(url);
  const queryParamsRegex = getUrlCatchSearchParamsRegex(url);
  await page.unroute(catchIdRegex);
  await page.route(catchIdRegex, async (route, request) => {
    const methods = request.method();
    if (methods === "GET") {
      await route.fulfill({ json: store.list[0] });
    }
  });

  await page.unroute(queryParamsRegex);
  await page.route(queryParamsRegex, async (route, request) => {
    const methods = request.method();
    if (methods === "GET") {
      await route.fulfill({ json: store.list });
    }
  });

  await mockPlaywrightCrud<CourseRun, DTOCourseRun>({
    data: store.courseRuns,
    routeUrl: "http://localhost:8071/api/v1.0/admin/users/",
    page,
  });

  await mockPlaywrightCrud<User, any>({
    data: store.users,
    routeUrl: "http://localhost:8071/api/v1.0/admin/users/",
    page,
  });
};

export const getEnrollmentListScenarioStore = (itemsNumber: number = 30) => {
  const list = transformEnrollmentsToEnrollmentListItems(
    EnrollmentFactory(itemsNumber),
  );
  const courseRuns: CourseRun[] = [];

  list.forEach((enrollment) => {
    courseRuns.push(enrollment.course_run);
  });

  return {
    list,
    courseRuns,
  };
};

export const mockAllEnrollmentItemsEntities = async (
  store: ReturnType<typeof getEnrollmentListScenarioStore>,
  page: Page,
) => {
  const url = "http://localhost:8071/api/v1.0/admin/enrollments/";
  const catchIdRegex = getUrlCatchIdRegex(url);
  const queryParamsRegex = getUrlCatchSearchParamsRegex(url);
  await page.unroute(catchIdRegex);
  await page.route(catchIdRegex, async (route, request) => {
    const methods = request.method();
    if (methods === "GET") {
      await route.fulfill({ json: store.list[0] });
    }
  });

  await page.unroute(queryParamsRegex);
  await page.route(queryParamsRegex, async (route, request) => {
    const methods = request.method();
    if (methods === "GET") {
      await route.fulfill({ json: store.list });
    }
  });

  await mockPlaywrightCrud<CourseRun, DTOCourseRun>({
    data: store.courseRuns,
    routeUrl: "http://localhost:8071/api/v1.0/admin/users/",
    page,
  });
};
