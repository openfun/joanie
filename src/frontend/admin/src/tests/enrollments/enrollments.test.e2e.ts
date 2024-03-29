import { expect, test } from "@playwright/test";
import moment from "moment";
import {
  getEnrollmentListScenarioStore,
  getEnrollmentsScenarioStore,
  mockAllEnrollmentItemsEntities,
  mockAllEnrollmentsEntities,
} from "@/tests/enrollments/EnrollmentsTestScenario";
import { PATH_ADMIN } from "@/utils/routes/path";
import { EnrollmentState } from "@/services/api/models/Enrollment";

test.describe("Enrollment view", () => {
  let store = getEnrollmentsScenarioStore();
  test.beforeEach(async ({ page }) => {
    store = getEnrollmentsScenarioStore();
    await mockAllEnrollmentsEntities(store, page);
  });

  test("Check all field are present and have the good value", async ({
    page,
  }) => {
    const enrollment = store.list[0];
    await page.goto(PATH_ADMIN.enrollments.list);
    await expect(
      page.getByRole("heading", { name: "Enrollments" }),
    ).toBeVisible();
    await page.getByRole("link", { name: enrollment.course_run.title }).click();
    await page.getByRole("heading", { name: "Enrollment view" }).click();
    await expect(
      page.getByRole("heading", { name: "Details of an enrollment" }),
    ).toBeVisible();

    await expect(page.getByLabel("Course run")).toHaveValue(
      enrollment.course_run.title,
    );
    await expect(page.getByLabel("User")).toHaveValue(
      enrollment.user.full_name,
    );

    const wasCreatedForOrder = page.getByLabel("Was created for an order");
    if (enrollment.was_created_by_order) {
      await expect(wasCreatedForOrder).toBeChecked();
    } else {
      await expect(wasCreatedForOrder).not.toBeChecked();
    }
    await expect(
      page.getByText(
        "Checked if the enrollment was originally created as part of an order.",
      ),
    ).toBeVisible();

    const isActiveCheckbox = page.getByLabel("Is active");
    if (enrollment.is_active) {
      await expect(isActiveCheckbox).toBeChecked();
    } else {
      await expect(isActiveCheckbox).not.toBeChecked();
    }
    await expect(
      page.getByText("Checked if the user is registered for the course run."),
    ).toBeVisible();
  });

  test("Check unroll actions when the enrollment is active and course_run_enrollment_end is not passed", async ({
    page,
  }) => {
    store = getEnrollmentsScenarioStore();
    store.list[0].is_active = true;
    store.list[0].course_run.enrollment_end = moment()
      .add("2", "days")
      .toISOString();
    await mockAllEnrollmentsEntities(store, page);
    const enrollment = store.list[0];
    await page.goto(PATH_ADMIN.enrollments.list);
    await expect(
      page.getByRole("heading", { name: "Enrollments" }),
    ).toBeVisible();
    await page.getByRole("link", { name: enrollment.course_run.title }).click();
    await page.getByRole("heading", { name: "Enrollment view" }).click();
    await page.getByTestId("enrollment-view-action-button").click();
    await expect(page.getByTestId("CancelIcon")).toBeVisible();
    await page.getByRole("menuitem", { name: "Unenroll" }).click();
    await expect(
      page.getByRole("heading", { name: "Unenroll this user" }),
    ).toBeVisible();

    await expect(page.getByRole("button", { name: "Unenroll" })).toBeVisible();
  });

  test("Check unroll actions when the enrollment is active and course_run_enrollment_end is passed", async ({
    page,
  }) => {
    store = getEnrollmentsScenarioStore();
    store.list[0].is_active = true;
    store.list[0].course_run.enrollment_end = moment()
      .subtract("2", "days")
      .toISOString();
    await mockAllEnrollmentsEntities(store, page);
    const enrollment = store.list[0];
    await page.goto(PATH_ADMIN.enrollments.list);
    await expect(
      page.getByRole("heading", { name: "Enrollments" }),
    ).toBeVisible();
    await page.getByRole("link", { name: enrollment.course_run.title }).click();
    await page.getByRole("heading", { name: "Enrollment view" }).click();
    await page.getByTestId("enrollment-view-action-button").click();
    await expect(page.getByTestId("CancelIcon")).toBeVisible();
    await page.getByRole("menuitem", { name: "unenroll" }).click();
    await expect(
      page.getByRole("heading", { name: "Unenroll this user" }),
    ).toBeVisible();
    await expect(
      page.getByText(
        `Are you sure you want to unenroll ${enrollment.user.full_name} to ${enrollment.course_run.title}`,
      ),
    ).toBeVisible();
    await expect(page.getByRole("button", { name: "Unenroll" })).toBeVisible();
  });

  test("Check enroll actions when the enrollment is not active and course_run_enrollment_end is not passed", async ({
    page,
  }) => {
    store = getEnrollmentsScenarioStore();
    store.list[0].is_active = false;
    store.list[0].course_run.enrollment_end = moment()
      .add("2", "days")
      .toISOString();
    await mockAllEnrollmentsEntities(store, page);
    const enrollment = store.list[0];
    await page.goto(PATH_ADMIN.enrollments.list);
    await expect(
      page.getByRole("heading", { name: "Enrollments" }),
    ).toBeVisible();
    await page.getByRole("link", { name: enrollment.course_run.title }).click();
    await page.getByRole("heading", { name: "Enrollment view" }).click();
    await page.getByTestId("enrollment-view-action-button").click();
    await expect(page.getByTestId("CheckCircleIcon")).toBeVisible();
    await expect(page.getByTestId("Enroll").getByText("Enroll")).toBeVisible();
  });

  test("Check that the message is displayed for a failed status", async ({
    page,
  }) => {
    store = getEnrollmentsScenarioStore();
    store.list[0].state = EnrollmentState.FAILED;
    await mockAllEnrollmentsEntities(store, page);
    const enrollment = store.list[0];
    await page.goto(PATH_ADMIN.enrollments.list);
    await expect(
      page.getByRole("heading", { name: "Enrollments" }),
    ).toBeVisible();
    await page.getByRole("link", { name: enrollment.course_run.title }).click();
    await page.getByRole("heading", { name: "Enrollment view" }).click();
    await expect(
      page.getByText("A problem occurred during enrollment on the LMS."),
    ).toBeVisible();
  });

  test("Check enroll actions when the enrollment is not active and course_run_enrollment_end is passed", async ({
    page,
  }) => {
    store = getEnrollmentsScenarioStore();
    store.list[0].is_active = false;
    store.list[0].course_run.enrollment_end = moment()
      .subtract("2", "days")
      .toISOString();
    await mockAllEnrollmentsEntities(store, page);
    const enrollment = store.list[0];
    await page.goto(PATH_ADMIN.enrollments.list);
    await expect(
      page.getByRole("heading", { name: "Enrollments" }),
    ).toBeVisible();
    await page.getByRole("link", { name: enrollment.course_run.title }).click();
    await page.getByRole("heading", { name: "Enrollment view" }).click();
    await page.getByTestId("enrollment-view-action-button").click();
    await page.getByTestId("Enroll").hover();
    await expect(
      page.getByText(
        "It's impossible to enroll because the course run is not opened for enrollment.",
      ),
    ).toBeVisible();
  });
});

test.describe("Enrollment list", () => {
  let store = getEnrollmentListScenarioStore(3);
  test.beforeEach(async ({ page }) => {
    store = getEnrollmentListScenarioStore(3);
    await mockAllEnrollmentItemsEntities(store, page);
  });

  test("Check if all enrollments are presents", async ({ page }) => {
    await page.goto(PATH_ADMIN.enrollments.list);
    await expect(
      page.getByRole("heading", { name: "Enrollments" }),
    ).toBeVisible();
    await Promise.all(
      store.list.map(async (option) => {
        const row = page.getByRole("row", { name: option.course_run.title });
        await expect(
          row.getByRole("gridcell", { name: option.course_run.title }),
        ).toBeVisible();
        await expect(
          row.getByRole("gridcell", { name: option.user_name }),
        ).toBeVisible();

        await expect(row.getByRole("checkbox")).toBeVisible();
      }),
    );
  });
});
