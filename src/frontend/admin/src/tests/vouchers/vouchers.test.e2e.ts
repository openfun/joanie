import { expect, test } from "@playwright/test";
import { mockPlaywrightCrud } from "@/tests/useResourceHandler";
import { PATH_ADMIN } from "@/utils/routes/path";
import { getVouchersScenarioStore } from "@/tests/vouchers/VouchersTestScenario";
import { DTOVoucher, Voucher } from "@/services/api/models/Voucher";
import {
  Discount,
  DTODiscount,
  getDiscountLabel,
} from "@/services/api/models/Discount";

const voucherApiUrl = "http://localhost:8071/api/v1.0/admin/vouchers/";

test.describe("Voucher view", () => {
  let store = getVouchersScenarioStore();

  test.beforeEach(async ({ page }) => {
    store = getVouchersScenarioStore();
    await mockPlaywrightCrud<Voucher, DTOVoucher>({
      data: store.list,
      routeUrl: voucherApiUrl,
      page,
      updateCallback: (payload, item) => ({
        ...item!,
        ...payload,
      }),
    });

    await mockPlaywrightCrud<Discount, DTODiscount>({
      data: store.discounts,
      routeUrl: "http://localhost:8071/api/v1.0/admin/discounts/",
      page,
    });
  });

  test("Check all fields have the good value", async ({ page }) => {
    const voucher = store.list[0];
    await page.goto(PATH_ADMIN.vouchers.list);
    await page.getByRole("heading", { name: "Vouchers" }).click();
    await page.getByRole("link", { name: voucher.code }).click();

    await expect(page.getByLabel("Voucher code")).toHaveValue(voucher.code);

    const mu = page.getByLabel("Multiple uses by the same user");
    const mus = page.getByLabel("Usable by multiple users");
    if (voucher.multiple_use) {
      await expect(mu).toBeChecked();
    } else {
      await expect(mu).not.toBeChecked();
    }
    if (voucher.multiple_users) {
      await expect(mus).toBeChecked();
    } else {
      await expect(mus).not.toBeChecked();
    }
  });
});

test.describe("Vouchers list view", () => {
  let store = getVouchersScenarioStore();

  test.beforeEach(async ({ page }) => {
    store = getVouchersScenarioStore();
    await mockPlaywrightCrud<Voucher, DTOVoucher>({
      data: store.list,
      routeUrl: voucherApiUrl,
      page,
    });
  });

  test("Check all the column are presents", async ({ page }) => {
    await page.goto(PATH_ADMIN.vouchers.list);
    await expect(page.getByRole("heading", { name: "Vouchers" })).toBeVisible();

    await expect(
      page.getByRole("columnheader", { name: "Code" }),
    ).toBeVisible();
    await expect(
      page.getByRole("columnheader", { name: "Discount" }),
    ).toBeVisible();
    await expect(
      page.getByRole("columnheader", { name: "Multiple use", exact: true }),
    ).toBeVisible();
    await expect(
      page.getByRole("columnheader", { name: "Multiple users", exact: true }),
    ).toBeVisible();
  });

  test("Check all the vouchers are presents", async ({ page }) => {
    await page.goto(PATH_ADMIN.vouchers.list);
    await expect(page.getByRole("heading", { name: "Vouchers" })).toBeVisible();
    await Promise.all(
      store.list.map(async (voucher) => {
        const rowLocator = page.locator(`[data-id='${voucher.id}']`);
        await expect(rowLocator).toBeVisible();
        await expect(
          rowLocator.getByRole("gridcell", { name: voucher.code }),
        ).toBeVisible();
        if (voucher.discount) {
          await expect(
            rowLocator.getByText(getDiscountLabel(voucher.discount)),
          ).toBeVisible();
        }
      }),
    );
  });

  test("Check ordering", async ({ page }) => {
    await page.goto(PATH_ADMIN.vouchers.list);

    const header = page.getByRole("columnheader", { name: "Code" });
    const field = await header.getAttribute("data-field");
    await header.click();

    let values = await page
      .locator(`[role='gridcell'][data-field='${field}']`)
      .allInnerTexts();
    expect(values).not.toHaveLength(0);
    expect(values).toEqual(values.toSorted());

    await header.click();
    await page.waitForLoadState("networkidle");

    values = await page
      .locator(`[role='gridcell'][data-field='${field}']`)
      .allInnerTexts();
    expect(values).not.toHaveLength(0);
    expect(values).toEqual(values.toSorted().reverse());
  });
});
