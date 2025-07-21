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
import { Offering, DTOOffering } from "@/services/api/models/Offerings";
import { OfferingRule } from "@/services/api/models/OfferingRule";
import {
  expectHaveClasses,
  expectHaveNotClasses,
  formatShortDateTest,
} from "@/tests/utils";
import {
  Discount,
  DTODiscount,
  getDiscountLabel,
} from "@/services/api/models/Discount";

const coursesApiUrl = "http://localhost:8071/api/v1.0/admin/courses/";
test.describe("Offering", () => {
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

    await mockPlaywrightCrud<Offering, DTOOffering>({
      data: store.offerings,
      routeUrl: "http://localhost:8071/api/v1.0/admin/offerings/",
      page,
      updateCallback: store.postOffering,
      createCallback: store.postOffering,
    });

    await mockPlaywrightCrud<Organization, DTOOrganization>({
      data: store.organizations,
      routeUrl: "http://localhost:8071/api/v1.0/admin/organizations/",
      page,
      createCallback: store.createOrg,
      optionsResult: ORGANIZATION_OPTIONS_REQUEST_RESULT,
    });

    await mockPlaywrightCrud<Discount, DTODiscount>({
      data: store.discounts,
      routeUrl: "http://localhost:8071/api/v1.0/admin/discounts/",
      page,
      createCallback: store.createDiscount,
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

  test("Check of the presence of all elements.", async ({ page }) => {
    const course = store.list[0];
    const offerings = course.offerings ?? [];
    await page.goto(PATH_ADMIN.courses.list);
    await store.mockCourseRunsFromCourse(page, []);
    await page.getByRole("link", { name: course.title }).click();
    await page.getByRole("tab", { name: "Products" }).click();

    await expect(
      page.locator('[id="__next"]').getByRole("alert"),
    ).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Offerings" }),
    ).toBeVisible();

    await Promise.all(
      offerings.map(async (offering) => {
        // Check if product title and organizations are shown
        await expect(
          page.getByRole("heading", { name: offering.product.title }),
        ).toHaveCount(1);
        const orgsTitle = offering.organizations.map((org) => org.title);
        await expect(page.getByText(orgsTitle.join(","))).toBeVisible();

        // Check if all offering rules for this offering are present
        const offeringRules = offering.offering_rules ?? [];
        await Promise.all(
          offeringRules.map(async (offeringRule, index) => {
            const usedSeats =
              (offeringRule.nb_seats ?? 0) -
              (offeringRule.nb_available_seats ?? 0);
            const start = await formatShortDateTest(page, offeringRule.start!);
            const end = await formatShortDateTest(page, offeringRule.end!);
            await expect(
              page.getByText(
                `Offering rule ${index + 1}` +
                  offeringRule.description +
                  `${usedSeats}/${offeringRule.nb_seats} seats` +
                  `From: ${start}` +
                  `To: ${end}` +
                  `Discount: ${getDiscountLabel(offeringRule.discount!)}`,
              ),
            ).toHaveCount(1);
          }),
        );
      }),
    );

    await expect(
      page.getByRole("button", { name: "Add offering", exact: true }),
    ).toBeVisible();

    await page
      .getByRole("button", { name: "Add offering", exact: true })
      .click();
    await expect(
      page.getByRole("heading", { name: "Add offering" }),
    ).toBeVisible();
    await expect(page.getByLabel("Choose your product")).toBeVisible();
    await expect(page.getByLabel("Search organization")).toBeVisible();
    await expect(page.getByTestId("submit-button-offering-form")).toBeVisible();
  });

  test("Render course form without offerings", async ({ page }) => {
    const course = store.list[0];
    course.offerings = [];
    await page.goto(PATH_ADMIN.courses.list);
    await store.mockCourseRunsFromCourse(page, []);
    await page.getByRole("link", { name: course.title }).click();
    await page.getByRole("tab", { name: "Products" }).click();
    await expect(
      page.getByText("No offering have been created for this course"),
    ).toBeVisible();
  });

  test("Create a new offering", async ({ page }) => {
    const course = store.list[0];
    course.offerings = [];
    await page.goto(PATH_ADMIN.courses.list);
    await store.mockCourseRunsFromCourse(page, []);
    await page.getByRole("link", { name: course.title }).click();
    await page.getByRole("tab", { name: "Products" }).click();

    await page.getByRole("button", { name: "Add offering" }).click();
    await page.getByLabel("Choose your product").click();
    await page.getByLabel("Choose your product").fill(store.products[0].title);
    await page.getByRole("option", { name: store.products[0].title }).click();
    const input = await page.getByLabel("Search organization");
    await input.fill(store.organizations[0].title);

    await page
      .getByRole("option", { name: store.organizations[0].title })
      .click();

    await expect(
      page.getByRole("heading", { name: store.organizations[0].title }),
    ).toBeVisible();

    await page.getByTestId("submit-button-offering-form").click();

    await expect(
      page.getByRole("heading", { name: store.products[0].title }),
    ).toBeVisible();
    await expect(page.getByText(store.organizations[0].title)).toBeVisible();
  });

  test("Copy url inside the clipboard", async ({ page, context }) => {
    await context.grantPermissions(["clipboard-read", "clipboard-write"]);
    const course = store.list[0];
    const offering = course.offerings![0];
    await page.goto(PATH_ADMIN.courses.list);
    await store.mockCourseRunsFromCourse(page, []);
    await page.getByRole("link", { name: course.title }).click();
    await page.getByRole("tab", { name: "Products" }).click();
    await page.getByTestId(`offering-actions-${offering.id}`).click();
    await page.getByRole("menuitem", { name: "Copy url" }).click();
    await expect(
      page.getByRole("alert").getByText("Link added to your clipboard"),
    ).toBeVisible();
    const handle = await page.evaluateHandle(() =>
      navigator.clipboard.readText(),
    );
    const clipboardContent = await handle.jsonValue();
    expect(clipboardContent).toEqual(offering.uri);
  });

  test("Add offering rule on offering", async ({ page }) => {
    await store.mockOfferingRule(
      page,
      store.offerings,
      store.offeringRules,
      store.discounts,
    );
    const course = store.list[0];
    await page.goto(PATH_ADMIN.courses.list);
    course.offerings = course.offerings ?? [];
    await store.mockCourseRunsFromCourse(page, []);
    await page.getByRole("link", { name: course.title }).click();
    await page.getByRole("tab", { name: "Products" }).click();
    await Promise.all(
      course.offerings.map(async (offering) => {
        await expect(
          page.getByRole("heading", { name: offering.product.title }),
        ).toBeVisible();
      }),
    );
    await page
      .getByRole("button", { name: "Add offering rule" })
      .first()
      .click();
    await page.getByRole("heading", { name: "Add an offering rule" }).click();
    await page.getByLabel("Number of seats").click();
    await page.getByLabel("Number of seats").fill("1919");
    await page
      .getByRole("textbox", { name: "Start date" })
      .fill("01/31/2023 10:00 AM");
    await page
      .getByRole("textbox", { name: "End date" })
      .fill("02/15/2023 10:00 AM");
    await page.getByRole("combobox", { name: "Discount" }).click();
    await page
      .getByRole("option", { name: getDiscountLabel(store.discounts[0]) })
      .click();

    await page.getByLabel("Activate this offering rule").check();
    await page.getByTestId("submit-button-offering-rule-form").click();
    const offeringRuleLength = course.offerings[0].offering_rules.length;
    const addedOfferingRule =
      course.offerings[0].offering_rules[offeringRuleLength - 1];
    await expect(
      page.getByText(`Offering rule ${offeringRuleLength}`),
    ).toBeVisible();
    await expect(page.getByText(`0/1919 seats`)).toBeVisible();
    await expect(
      page.getByText(`Discount: ${getDiscountLabel(store.discounts[0])}`),
    ).toBeVisible();
    await expect(page.getByText("From: 1/31/23, 10:00 AM")).toBeVisible();
    await expect(page.getByText("To: 2/15/23, 10:00 AM")).toBeVisible();

    await expect(
      page.getByTestId(
        `is-active-switch-offering-rule-${addedOfferingRule.id}`,
      ),
    ).toBeVisible();
  });

  test("Toggle is active switch on an offering rule", async ({ page }) => {
    const course = store.list[0];
    const offeringRule = course.offerings?.[0]
      .offering_rules[0] as OfferingRule;
    offeringRule.can_edit = true;
    offeringRule.is_active = true;
    await store.mockCourseRunsFromCourse(page, []);
    await store.mockOfferingRule(
      page,
      store.offerings,
      store.offeringRules,
      store.discounts,
    );
    await page.goto(PATH_ADMIN.courses.list);
    await page.getByRole("link", { name: course.title }).click();
    await page.getByRole("tab", { name: "Products" }).click();
    await expect(
      page.getByRole("heading", { name: `Edit course: ${course.title}` }),
    ).toBeVisible();

    const offeringRuleSwitchLocator = page.getByTestId(
      `is-active-switch-offering-rule-${offeringRule.id}`,
    );
    await expectHaveClasses(offeringRuleSwitchLocator, "Mui-checked");
    await offeringRuleSwitchLocator.click();
    await expectHaveNotClasses(offeringRuleSwitchLocator, "Mui-checked");
  });

  test("Edit an offering rule", async ({ page }) => {
    await store.mockCourseRunsFromCourse(page, []);
    const course = store.list[0];
    let offeringRule = course.offerings?.[0].offering_rules[0] as OfferingRule;

    offeringRule.can_edit = true;
    offeringRule.is_active = true;
    await store.mockOfferingRule(
      page,
      store.offerings,
      store.offeringRules,
      store.discounts,
    );
    await page.goto(PATH_ADMIN.courses.list);
    await page.getByRole("link", { name: course.title }).click();
    await page.getByRole("tab", { name: "Products" }).click();
    await expect(
      page.getByRole("heading", { name: `Edit course: ${course.title}` }),
    ).toBeVisible();

    const offeringRuleRowLocator = page.getByTestId(
      `offering-rule-${offeringRule.id}`,
    );

    await offeringRuleRowLocator.hover();
    await offeringRuleRowLocator.getByTestId("edit-row-button").click();

    await page.getByRole("heading", { name: "Edit an offering rule" }).click();
    await page.getByLabel("Number of seats").click();
    await page.getByLabel("Number of seats").fill("999999");
    await page.getByTestId("submit-button-offering-rule-form").click();
    offeringRule = course.offerings?.[0].offering_rules[0] as OfferingRule;

    const usedSeats =
      (offeringRule.nb_seats ?? 0) - (offeringRule.nb_available_seats ?? 0);
    const start = await formatShortDateTest(page, offeringRule.start!);
    const end = await formatShortDateTest(page, offeringRule.end!);
    await expect(
      page.getByText(
        "Offering rule 1" +
          offeringRule.description +
          `${usedSeats}/999999 seats` +
          `From: ${start}` +
          `To: ${end}`,
      ),
    ).toHaveCount(1);
  });

  test("Delete offering rule", async ({ page }) => {
    await store.mockCourseRunsFromCourse(page, []);
    await store.mockOfferingRule(
      page,
      store.offerings,
      store.offeringRules,
      store.discounts,
    );
    const course = store.list[0];
    const offeringRule = course.offerings?.[0]
      .offering_rules[0] as OfferingRule;
    offeringRule.can_edit = true;
    await page.goto(PATH_ADMIN.courses.list);
    await page.getByRole("link", { name: course.title }).click();
    await page.getByRole("tab", { name: "Products" }).click();
    await expect(
      page.getByRole("heading", { name: `Edit course: ${course.title}` }),
    ).toBeVisible();

    const usedSeats =
      (offeringRule.nb_seats ?? 0) - (offeringRule.nb_available_seats ?? 0);
    const start = await formatShortDateTest(page, offeringRule.start!);
    const end = await formatShortDateTest(page, offeringRule.end!);
    const offeringRuleLocator = page.getByText(
      "Offering rule 1" +
        offeringRule.description +
        `${usedSeats}/${offeringRule.nb_seats} seats` +
        `From: ${start}` +
        `To: ${end}`,
    );

    await expect(offeringRuleLocator).toHaveCount(1);

    await page.getByTestId(`offering-rule-${offeringRule?.id}`).hover();
    await page.getByTestId(`delete-offering-rule-${offeringRule?.id}`).click();
    await expect(
      page.getByRole("heading", { name: "Delete an offering rule" }),
    ).toBeVisible();
    await expect(
      page.getByText("Are you sure you want to delete this offering rule?"),
    ).toBeVisible();
    await page.getByRole("button", { name: "Validate" }).click();
    await expect(offeringRuleLocator).toHaveCount(0);
  });

  test("Create discount", async ({ page }) => {
    await store.mockOfferingRule(
      page,
      store.offerings,
      store.offeringRules,
      store.discounts,
    );
    const course = store.list[0];
    await page.goto(PATH_ADMIN.courses.list);
    course.offerings = course.offerings ?? [];
    await store.mockCourseRunsFromCourse(page, []);
    await page.getByRole("link", { name: course.title }).click();
    await page.getByRole("tab", { name: "Products" }).click();
    await Promise.all(
      course.offerings.map(async (offering) => {
        await expect(
          page.getByRole("heading", { name: offering.product.title }),
        ).toBeVisible();
      }),
    );
    await page
      .getByRole("button", { name: "Add offering rule" })
      .first()
      .click();
    await page.getByRole("heading", { name: "Add an offering rule" }).click();
    await page.getByTestId("search-add-button").click();
    await expect(
      page.getByRole("heading", { name: "Add a discount" }),
    ).toBeVisible();
    await page.getByRole("spinbutton", { name: "Rate (%)" }).fill("10");
    await page.getByRole("button", { name: "Submit" }).click();
    await expect(
      page.getByRole("heading", { name: "Add an offering rule" }),
    ).toBeVisible();
    await page.getByRole("button", { name: "Submit" }).click();
    await expect(page.getByText("Offering rule 3Discount: 10%")).toBeVisible();
  });

  test("Add a new discount", async ({ page }) => {
    await store.mockOfferingRule(
      page,
      store.offerings,
      store.offeringRules,
      store.discounts,
    );
    const course = store.list[0];
    await page.goto(PATH_ADMIN.courses.list);
    course.offerings = course.offerings ?? [];
    await store.mockCourseRunsFromCourse(page, []);
    await page.getByRole("link", { name: course.title }).click();
    await page.getByRole("tab", { name: "Products" }).click();
    await Promise.all(
      course.offerings.map(async (offering) => {
        await expect(
          page.getByRole("heading", { name: offering.product.title }),
        ).toBeVisible();
      }),
    );
    await page
      .getByRole("button", { name: "Add offering rule" })
      .first()
      .click();
    await page.getByRole("heading", { name: "Add an offering rule" }).click();
    await page.getByTestId("search-add-button").click();
    await expect(
      page.getByRole("heading", { name: "Add a discount" }),
    ).toBeVisible();
    await page.getByRole("spinbutton", { name: "Rate (%)" }).fill("10");
    await page.getByRole("button", { name: "Submit" }).click();
    await page.getByTestId("search-add-button").click();
    await expect(
      page.getByRole("heading", { name: "Add a discount" }),
    ).toBeVisible();
    await page.getByRole("spinbutton", { name: "Amount (€)" }).fill("33");
    await page.getByRole("button", { name: "Submit" }).click();
    await expect(
      page.getByRole("heading", { name: "Add an offering rule" }),
    ).toBeVisible();
    await page.getByRole("button", { name: "Submit" }).click();
    await expect(page.getByText("Offering rule 3Discount: 33 €")).toBeVisible();
  });

  test("Empty date field", async ({ page }) => {
    await store.mockOfferingRule(
      page,
      store.offerings,
      store.offeringRules,
      store.discounts,
    );
    const course = store.list[0];
    await page.goto(PATH_ADMIN.courses.list);
    course.offerings = course.offerings ?? [];
    await store.mockCourseRunsFromCourse(page, []);
    await page.getByRole("link", { name: course.title }).click();
    await page.getByRole("tab", { name: "Products" }).click();
    await Promise.all(
      course.offerings.map(async (offering) => {
        await expect(
          page.getByRole("heading", { name: offering.product.title }),
        ).toBeVisible();
      }),
    );
    await page
      .getByRole("button", { name: "Add offering rule" })
      .first()
      .click();
    await page.getByRole("heading", { name: "Add an offering rule" }).click();
    await page
      .getByRole("textbox", { name: "Start date" })
      .fill("01/31/2023 10:00 AM");
    await page.getByTitle("Clear").first().click();
    await page.getByRole("button", { name: "Submit" }).click();
    await expect(page.getByText("From: 1/31/23, 10:00 AM")).not.toBeVisible();
  });
});
