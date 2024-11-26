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
import { OrderGroup } from "@/services/api/models/OrderGroup";
import { expectHaveClasses, expectHaveNotClasses } from "@/tests/utils";

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

        // Check if all order group for this relation are presents
        const orderGroups = relation.order_groups ?? [];
        await Promise.all(
          orderGroups.map(async (orderGroup, index) => {
            await expect(
              page.getByText(
                `Order group ${index + 1}${
                  orderGroup.nb_seats - orderGroup.nb_available_seats
                }/${orderGroup.nb_seats} seats`,
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

  test("Add order group on course product relation", async ({ page }) => {
    await store.mockOrderGroup(page, store.productRelations, store.orderGroups);
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
    await page.getByRole("button", { name: "Add order group" }).first().click();
    await page.getByRole("heading", { name: "Add an order group" }).click();
    await page.getByLabel("Number of seats").click();
    await page.getByLabel("Number of seats").fill("1919");
    await page.getByLabel("Activate this order group").check();
    await page.getByTestId("submit-button-order-group-form").click();
    const orderGroupLength = course.product_relations[0].order_groups.length;
    const addedOrderGroup =
      course.product_relations[0].order_groups[orderGroupLength - 1];
    await expect(
      page.getByText(`Order group ${orderGroupLength}0/1919 seats`),
    ).toBeVisible();
    await expect(
      page.getByTestId(`is-active-switch-order-group-${addedOrderGroup.id}`),
    ).toBeVisible();
  });

  test("Toggle is active switch on an order group", async ({ page }) => {
    const course = store.list[0];
    const orderGroup = course.product_relations?.[0]
      .order_groups[0] as OrderGroup;
    orderGroup.can_edit = true;
    orderGroup.is_active = true;
    await store.mockCourseRunsFromCourse(page, []);
    await store.mockOrderGroup(page, store.productRelations, store.orderGroups);
    await page.goto(PATH_ADMIN.courses.list);
    await page.getByRole("link", { name: course.title }).click();
    await page.getByRole("tab", { name: "Products" }).click();
    await expect(
      page.getByRole("heading", { name: `Edit course: ${course.title}` }),
    ).toBeVisible();

    const orderGroupSwitchLocator = page.getByTestId(
      `is-active-switch-order-group-${orderGroup.id}`,
    );
    await expectHaveClasses(orderGroupSwitchLocator, "Mui-checked");
    await orderGroupSwitchLocator.click();
    await expectHaveNotClasses(orderGroupSwitchLocator, "Mui-checked");
  });

  test("Edit an order group", async ({ page }) => {
    await store.mockCourseRunsFromCourse(page, []);
    const course = store.list[0];
    let orderGroup = course.product_relations?.[0]
      .order_groups[0] as OrderGroup;
    orderGroup.can_edit = true;
    orderGroup.is_active = true;
    await store.mockOrderGroup(page, store.productRelations, store.orderGroups);
    await page.goto(PATH_ADMIN.courses.list);
    await page.getByRole("link", { name: course.title }).click();
    await page.getByRole("tab", { name: "Products" }).click();
    await expect(
      page.getByRole("heading", { name: `Edit course: ${course.title}` }),
    ).toBeVisible();

    const orderGroupRowLocator = page.getByTestId(
      `order-group-${orderGroup.id}`,
    );

    await orderGroupRowLocator.hover();
    await orderGroupRowLocator.getByTestId("edit-row-button").click();

    await page.getByRole("heading", { name: "Edit an order group" }).click();
    await page.getByLabel("Number of seats").click();
    await page.getByLabel("Number of seats").fill("999999");
    await page.getByTestId("submit-button-order-group-form").click();
    orderGroup = course.product_relations?.[0].order_groups[0] as OrderGroup;

    await expect(
      orderGroupRowLocator.getByText(
        `Order group 1${
          orderGroup.nb_seats - orderGroup.nb_available_seats
        }/999999 seats`,
      ),
    ).toHaveCount(1);
  });

  test("Delete order group", async ({ page }) => {
    await store.mockCourseRunsFromCourse(page, []);
    await store.mockOrderGroup(page, store.productRelations, store.orderGroups);
    const course = store.list[0];
    const orderGroup = course.product_relations?.[0]
      .order_groups[0] as OrderGroup;
    orderGroup.can_edit = true;
    await page.goto(PATH_ADMIN.courses.list);
    await page.getByRole("link", { name: course.title }).click();
    await page.getByRole("tab", { name: "Products" }).click();
    await expect(
      page.getByRole("heading", { name: `Edit course: ${course.title}` }),
    ).toBeVisible();

    const orderGroupLocator = page.getByText(
      `Order group 1${orderGroup.nb_seats - orderGroup.nb_available_seats}/${
        orderGroup.nb_seats
      } seats`,
    );

    await expect(orderGroupLocator).toHaveCount(1);

    await page.getByTestId(`order-group-${orderGroup?.id}`).hover();
    await page.getByTestId(`delete-order-group-${orderGroup?.id}`).click();
    await expect(
      page.getByRole("heading", { name: "Delete an order group" }),
    ).toBeVisible();
    await expect(
      page.getByText("Are you sure you want to delete this order group?"),
    ).toBeVisible();
    await page.getByRole("button", { name: "Validate" }).click();
    await expect(orderGroupLocator).toHaveCount(0);
  });
});
