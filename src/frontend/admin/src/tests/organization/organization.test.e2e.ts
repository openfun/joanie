import { expect, test } from "@playwright/test";
import { getOrganizationScenarioStore } from "@/tests/organization/OrganizationTestScenario";
import { mockPlaywrightCrud } from "@/tests/useResourceHandler";
import {
  DTOOrganization,
  Organization,
} from "@/services/api/models/Organization";
import { PATH_ADMIN } from "@/utils/routes/path";
import { ORGANIZATION_OPTIONS_REQUEST_RESULT } from "@/tests/mocks/organizations/organization-mock";
import { User } from "@/services/api/models/User";
import { expectHaveClasses } from "@/tests/utils";

const searchPlaceholder = "Search by title, code";

test.describe("Organization Form", () => {
  let store = getOrganizationScenarioStore();
  test.beforeEach(async ({ page }) => {
    store = getOrganizationScenarioStore();
    await mockPlaywrightCrud<Organization, DTOOrganization>({
      data: store.list,
      routeUrl: "http://localhost:8071/api/v1.0/admin/organizations/",
      page,
      createCallback: store.postUpdate,
      updateCallback: store.postUpdate,
      searchResult: store.list[0],
      optionsResult: ORGANIZATION_OPTIONS_REQUEST_RESULT,
    });

    await mockPlaywrightCrud<User, any>({
      data: store.userList,
      routeUrl: "http://localhost:8071/api/v1.0/admin/users/",
      page,
    });
  });
  test("Create a new certificate definition", async ({ page }) => {
    await page.goto(PATH_ADMIN.organizations.list);
    // Go to the form
    await page.getByRole("button", { name: "Add" }).click();
    await expect(
      page.getByRole("heading", { name: "Add organization" }),
    ).toBeVisible();

    // Fill the form and submit
    await page.getByRole("button", { name: "Add" }).click();
    await page.getByLabel("Title").click();
    await page.getByLabel("Title").fill("Organization test");
    await page.getByLabel("Title").fill("Organization title");
    await page.getByLabel("Code", { exact: true }).click();
    await page.getByLabel("Code", { exact: true }).fill("Organization code");
    await page.getByLabel("Country").click();
    await page.getByRole("option", { name: "United Kingdom" }).click();
    await page.getByLabel("Representative", { exact: true }).click();
    await page.getByLabel("Representative", { exact: true }).fill("John Doe");

    await expect(
      page.getByText("Mandatory if signatory representative is set"),
    ).toBeVisible();

    await page.getByLabel("Profession of the representative").click();
    await page.getByLabel("Profession of the representative").fill("Director");
    await page.getByLabel("Signatory representative", { exact: true }).click();

    await page
      .getByLabel("Signatory representative", { exact: true })
      .fill("Doe John");
    await page.getByRole("button", { name: "Submit" }).click();
    await expectHaveClasses(
      page.getByText("signatory_representative_profession is a required field"),
      "Mui-error",
    );

    await page.getByLabel("Profession of the signatory").click();
    await page.getByLabel("Profession of the signatory").fill("CTO");
    await page.getByLabel("Enterprise code").click();
    await page.getByLabel("Enterprise code").fill("0001");
    await page.getByLabel("Activity category code").click();
    await page.getByLabel("Activity category code").fill("00002");
    await page.getByLabel("Contact phone").click();
    await page.getByLabel("Contact phone").fill("0000000000");
    await page.getByLabel("Contact email", { exact: true }).click();
    await page
      .getByLabel("Contact email", { exact: true })
      .fill("john.doe@yopmail.com");
    await page.getByLabel("Contact email", { exact: true }).press("Tab");
    await page.getByLabel("DPO Contact email").fill("dpo.contact@gmail.com");
    await expect(page.getByRole("heading", { name: "Contact" })).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Legal part" }),
    ).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Signatory details" }),
    ).toBeVisible();
    await page.getByRole("button", { name: "Submit" }).click();

    // Get the successfully notification
    await expect(
      page.getByText("Operation completed successfully."),
    ).toBeVisible();

    await expect(
      page.getByRole("heading", {
        name: "Edit organization: Organization title",
      }),
    ).toHaveCount(1);

    await expect(page.getByText("Organization members")).toBeVisible();

    // Go to the list, and check that the new certificate definition is present in the list
    await page.getByRole("link", { name: "List" }).click();

    await expect(
      page.getByRole("heading", { name: "Organizations" }),
    ).toHaveCount(1);
    await expect(
      page.getByRole("row", {
        name: `Organization code Organization title`,
      }),
    ).toHaveCount(1);
  });
});

test.describe("Organization List", () => {
  let store = getOrganizationScenarioStore();
  test.beforeEach(async ({ page }) => {
    store = getOrganizationScenarioStore();
    await mockPlaywrightCrud<Organization, DTOOrganization>({
      data: store.list,
      routeUrl: "http://localhost:8071/api/v1.0/admin/organizations/",
      page,
      createCallback: store.postUpdate,
      updateCallback: store.postUpdate,
      searchResult: store.list[0],
    });
  });

  test("Render the entire list and check that all elements are present", async ({
    page,
  }) => {
    await page.goto(PATH_ADMIN.organizations.list);

    await expect(
      page.getByRole("heading", { name: "Organizations" }),
    ).toHaveCount(1);

    await expect(page.getByPlaceholder(searchPlaceholder)).toBeVisible();
    await Promise.all(
      store.list.map(async (org) => {
        await expect(page.getByText(org.title)).toBeVisible();
        await expect(page.getByText(org.code)).toBeVisible();
        await expect(
          page
            .getByRole("row", { name: `${org.code} ${org.title}` })
            .getByRole("button"),
        ).toHaveCount(1);
      }),
    );
  });
  test("Render the entire list and use search", async ({ page }) => {
    await mockPlaywrightCrud<Organization, DTOOrganization>({
      data: store.list,
      routeUrl: "http://localhost:8071/api/v1.0/admin/organizations/",
      page,
      searchTimeout: 200,
      searchResult: store.list[0],
    });
    await page.goto(PATH_ADMIN.organizations.list);

    await expect(
      page.getByRole("heading", { name: "Organizations" }),
    ).toHaveCount(1);

    await expect(page.getByPlaceholder(searchPlaceholder)).toBeVisible();
    await expect(page.getByText(store.list[1].title)).toBeVisible();
    await page.getByPlaceholder(searchPlaceholder).fill(store.list[0].title);
    await expect(page.getByTestId("circular-loader-container")).toBeVisible();
    await expect(page.getByTestId("circular-loader-container")).toBeHidden();
    await expect(page.getByText(store.list[1].title)).toBeHidden();
    await expect(page.getByText(store.list[0].title)).toBeVisible();
    await page.getByPlaceholder(searchPlaceholder).fill("");
    await expect(page.getByTestId("circular-loader-container")).toBeVisible();
    await expect(page.getByTestId("circular-loader-container")).toBeHidden();
    await expect(page.getByText(store.list[1].title)).toBeVisible();
  });

  test("Delete an organization", async ({ page }) => {
    const organizationToDelete = store.list[0];
    await page.goto(PATH_ADMIN.organizations.list);
    await expect(
      page.getByRole("heading", { name: "Organizations" }),
    ).toHaveCount(1);
    await page
      .getByRole("row", {
        name: `${organizationToDelete.code} ${organizationToDelete.title}`,
      })
      .getByRole("button")
      .click();
    await page.getByRole("menuitem", { name: "Delete" }).click();
    await page.getByRole("heading", { name: "Delete an entity" }).click();
    await page
      .getByText(
        `Are you sure you want to delete this entity (${organizationToDelete.title}) ?`,
      )
      .click();
    await page.getByRole("button", { name: "Validate" }).click();
    await page.getByText("Operation completed successfully.").click();
    await expect(
      page
        .getByRole("row", {
          name: `${organizationToDelete.code} ${organizationToDelete.title}`,
        })
        .getByRole("button"),
    ).toHaveCount(0);
  });
});
