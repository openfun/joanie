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
import {
  CourseProductRelation,
  DTOCourseProductRelation,
} from "@/services/api/models/Relations";
import { OfferRule } from "@/services/api/models/OfferRule";
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

    await mockPlaywrightCrud<CourseProductRelation, DTOCourseProductRelation>({
      data: store.productRelations,
      routeUrl:
        "http://localhost:8071/api/v1.0/admin/course-product-relations/",
      page,
      updateCallback: store.postProductRelation,
      createCallback: store.postProductRelation,
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
    const relations = course.product_relations ?? [];
    await page.goto(PATH_ADMIN.courses.list);
    await store.mockCourseRunsFromCourse(page, []);
    await page.getByRole("link", { name: course.title }).click();
    await page.getByRole("tab", { name: "Products" }).click();

    await expect(
      page.locator('[id="__next"]').getByRole("alert"),
    ).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Relation to products" }),
    ).toBeVisible();

    await Promise.all(
      relations.map(async (relation) => {
        // Check if product title and organizations are shown
        await expect(
          page.getByRole("heading", { name: relation.product.title }),
        ).toHaveCount(1);
        const orgsTitle = relation.organizations.map((org) => org.title);
        await expect(page.getByText(orgsTitle.join(","))).toBeVisible();

        // Check if all offer rules for this relation are present
        const offerRules = relation.offer_rules ?? [];
        await Promise.all(
          offerRules.map(async (offerRule, index) => {
            const usedSeats =
              (offerRule.nb_seats ?? 0) - (offerRule.nb_available_seats ?? 0);
            const start = await formatShortDateTest(page, offerRule.start!);
            const end = await formatShortDateTest(page, offerRule.end!);
            await expect(
              page.getByText(
                `Offer rule ${index + 1}` +
                  offerRule.description +
                  `${usedSeats}/${offerRule.nb_seats} seats` +
                  `From: ${start}` +
                  `To: ${end}` +
                  `Discount: ${getDiscountLabel(offerRule.discount!)}`,
              ),
            ).toHaveCount(1);
          }),
        );
      }),
    );

    await expect(
      page.getByRole("button", { name: "Add relation" }),
    ).toBeVisible();

    await page.getByRole("button", { name: "Add relation" }).click();
    await expect(
      page.getByRole("heading", { name: "Add the relation" }),
    ).toBeVisible();
    await expect(page.getByLabel("Choose your product")).toBeVisible();
    await expect(page.getByLabel("Search organization")).toBeVisible();
    await expect(
      page.getByTestId("submit-button-course-relation-to-products-form"),
    ).toBeVisible();
  });

  test("Render course form without relations", async ({ page }) => {
    const course = store.list[0];
    course.product_relations = [];
    await page.goto(PATH_ADMIN.courses.list);
    await store.mockCourseRunsFromCourse(page, []);
    await page.getByRole("link", { name: course.title }).click();
    await page.getByRole("tab", { name: "Products" }).click();
    await expect(
      page.getByText(
        "No product relationships have been created for this course",
      ),
    ).toBeVisible();
  });

  test("Create a new course product relation", async ({ page }) => {
    const course = store.list[0];
    course.product_relations = [];
    await page.goto(PATH_ADMIN.courses.list);
    await store.mockCourseRunsFromCourse(page, []);
    await page.getByRole("link", { name: course.title }).click();
    await page.getByRole("tab", { name: "Products" }).click();

    await page.getByRole("button", { name: "Add relation" }).click();
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

    await page
      .getByTestId("submit-button-course-relation-to-products-form")
      .click();

    await expect(
      page.getByRole("heading", { name: store.products[0].title }),
    ).toBeVisible();
    await expect(page.getByText(store.organizations[0].title)).toBeVisible();
  });

  test("Copy url inside the clipboard", async ({ page, context }) => {
    await context.grantPermissions(["clipboard-read", "clipboard-write"]);
    const course = store.list[0];
    const relation = course.product_relations![0];
    await page.goto(PATH_ADMIN.courses.list);
    await store.mockCourseRunsFromCourse(page, []);
    await page.getByRole("link", { name: course.title }).click();
    await page.getByRole("tab", { name: "Products" }).click();
    await page
      .getByTestId(`course-product-relation-actions-${relation.id}`)
      .click();
    await page.getByRole("menuitem", { name: "Copy url" }).click();
    await expect(
      page.getByRole("alert").getByText("Link added to your clipboard"),
    ).toBeVisible();
    const handle = await page.evaluateHandle(() =>
      navigator.clipboard.readText(),
    );
    const clipboardContent = await handle.jsonValue();
    expect(clipboardContent).toEqual(relation.uri);
  });

  test("Add offer rule on course product relation", async ({ page }) => {
    await store.mockOfferRule(
      page,
      store.productRelations,
      store.offerRules,
      store.discounts,
    );
    const course = store.list[0];
    await page.goto(PATH_ADMIN.courses.list);
    course.product_relations = course.product_relations ?? [];
    await store.mockCourseRunsFromCourse(page, []);
    await page.getByRole("link", { name: course.title }).click();
    await page.getByRole("tab", { name: "Products" }).click();
    await Promise.all(
      course.product_relations.map(async (relation) => {
        await expect(
          page.getByRole("heading", { name: relation.product.title }),
        ).toBeVisible();
      }),
    );
    await page.getByRole("button", { name: "Add offer rule" }).first().click();
    await page.getByRole("heading", { name: "Add an offer rule" }).click();
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

    await page.getByLabel("Activate this offer rule").check();
    await page.getByTestId("submit-button-offer-rule-form").click();
    const offerRuleLength = course.product_relations[0].offer_rules.length;
    const addedOfferRule =
      course.product_relations[0].offer_rules[offerRuleLength - 1];
    await expect(page.getByText(`Offer rule ${offerRuleLength}`)).toBeVisible();
    await expect(page.getByText(`0/1919 seats`)).toBeVisible();
    await expect(
      page.getByText(`Discount: ${getDiscountLabel(store.discounts[0])}`),
    ).toBeVisible();
    await expect(page.getByText("From: 1/31/23, 10:00 AM")).toBeVisible();
    await expect(page.getByText("To: 2/15/23, 10:00 AM")).toBeVisible();

    await expect(
      page.getByTestId(`is-active-switch-offer-rule-${addedOfferRule.id}`),
    ).toBeVisible();
  });

  test("Toggle is active switch on an offer rule", async ({ page }) => {
    const course = store.list[0];
    const offerRule = course.product_relations?.[0].offer_rules[0] as OfferRule;
    offerRule.can_edit = true;
    offerRule.is_active = true;
    await store.mockCourseRunsFromCourse(page, []);
    await store.mockOfferRule(
      page,
      store.productRelations,
      store.offerRules,
      store.discounts,
    );
    await page.goto(PATH_ADMIN.courses.list);
    await page.getByRole("link", { name: course.title }).click();
    await page.getByRole("tab", { name: "Products" }).click();
    await expect(
      page.getByRole("heading", { name: `Edit course: ${course.title}` }),
    ).toBeVisible();

    const offerRuleSwitchLocator = page.getByTestId(
      `is-active-switch-offer-rule-${offerRule.id}`,
    );
    await expectHaveClasses(offerRuleSwitchLocator, "Mui-checked");
    await offerRuleSwitchLocator.click();
    await expectHaveNotClasses(offerRuleSwitchLocator, "Mui-checked");
  });

  test("Edit an offer rule", async ({ page }) => {
    await store.mockCourseRunsFromCourse(page, []);
    const course = store.list[0];
    let offerRule = course.product_relations?.[0].offer_rules[0] as OfferRule;

    offerRule.can_edit = true;
    offerRule.is_active = true;
    await store.mockOfferRule(
      page,
      store.productRelations,
      store.offerRules,
      store.discounts,
    );
    await page.goto(PATH_ADMIN.courses.list);
    await page.getByRole("link", { name: course.title }).click();
    await page.getByRole("tab", { name: "Products" }).click();
    await expect(
      page.getByRole("heading", { name: `Edit course: ${course.title}` }),
    ).toBeVisible();

    const offerRuleRowLocator = page.getByTestId(`offer-rule-${offerRule.id}`);

    await offerRuleRowLocator.hover();
    await offerRuleRowLocator.getByTestId("edit-row-button").click();

    await page.getByRole("heading", { name: "Edit an offer rule" }).click();
    await page.getByLabel("Number of seats").click();
    await page.getByLabel("Number of seats").fill("999999");
    await page.getByTestId("submit-button-offer-rule-form").click();
    offerRule = course.product_relations?.[0].offer_rules[0] as OfferRule;

    const usedSeats =
      (offerRule.nb_seats ?? 0) - (offerRule.nb_available_seats ?? 0);
    const start = await formatShortDateTest(page, offerRule.start!);
    const end = await formatShortDateTest(page, offerRule.end!);
    await expect(
      page.getByText(
        "Offer rule 1" +
          offerRule.description +
          `${usedSeats}/999999 seats` +
          `From: ${start}` +
          `To: ${end}`,
      ),
    ).toHaveCount(1);
  });

  test("Delete offer rule", async ({ page }) => {
    await store.mockCourseRunsFromCourse(page, []);
    await store.mockOfferRule(
      page,
      store.productRelations,
      store.offerRules,
      store.discounts,
    );
    const course = store.list[0];
    const offerRule = course.product_relations?.[0].offer_rules[0] as OfferRule;
    offerRule.can_edit = true;
    await page.goto(PATH_ADMIN.courses.list);
    await page.getByRole("link", { name: course.title }).click();
    await page.getByRole("tab", { name: "Products" }).click();
    await expect(
      page.getByRole("heading", { name: `Edit course: ${course.title}` }),
    ).toBeVisible();

    const usedSeats =
      (offerRule.nb_seats ?? 0) - (offerRule.nb_available_seats ?? 0);
    const start = await formatShortDateTest(page, offerRule.start!);
    const end = await formatShortDateTest(page, offerRule.end!);
    const offerRuleLocator = page.getByText(
      "Offer rule 1" +
        offerRule.description +
        `${usedSeats}/${offerRule.nb_seats} seats` +
        `From: ${start}` +
        `To: ${end}`,
    );

    await expect(offerRuleLocator).toHaveCount(1);

    await page.getByTestId(`offer-rule-${offerRule?.id}`).hover();
    await page.getByTestId(`delete-offer-rule-${offerRule?.id}`).click();
    await expect(
      page.getByRole("heading", { name: "Delete an offer rule" }),
    ).toBeVisible();
    await expect(
      page.getByText("Are you sure you want to delete this offer rule?"),
    ).toBeVisible();
    await page.getByRole("button", { name: "Validate" }).click();
    await expect(offerRuleLocator).toHaveCount(0);
  });

  test("Create discount", async ({ page }) => {
    await store.mockOfferRule(
      page,
      store.productRelations,
      store.offerRules,
      store.discounts,
    );
    const course = store.list[0];
    await page.goto(PATH_ADMIN.courses.list);
    course.product_relations = course.product_relations ?? [];
    await store.mockCourseRunsFromCourse(page, []);
    await page.getByRole("link", { name: course.title }).click();
    await page.getByRole("tab", { name: "Products" }).click();
    await Promise.all(
      course.product_relations.map(async (relation) => {
        await expect(
          page.getByRole("heading", { name: relation.product.title }),
        ).toBeVisible();
      }),
    );
    await page.getByRole("button", { name: "Add offer rule" }).first().click();
    await page.getByRole("heading", { name: "Add an offer rule" }).click();
    await page.getByTestId("search-add-button").click();
    await expect(
      page.getByRole("heading", { name: "Add a discount" }),
    ).toBeVisible();
    await page.getByRole("spinbutton", { name: "Rate (%)" }).fill("10");
    await page.getByRole("button", { name: "Submit" }).click();
    await expect(
      page.getByRole("heading", { name: "Add an offer rule" }),
    ).toBeVisible();
    await page.getByRole("button", { name: "Submit" }).click();
    await expect(page.getByText("Offer rule 3Discount: 10%")).toBeVisible();
  });
});
