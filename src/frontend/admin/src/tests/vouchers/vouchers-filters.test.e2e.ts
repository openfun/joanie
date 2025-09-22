import { expect, test } from "@playwright/test";
import { mockPlaywrightCrud } from "@/tests/useResourceHandler";
import { PATH_ADMIN } from "@/utils/routes/path";
import { getVouchersScenarioStore } from "@/tests/vouchers/VouchersTestScenario";
import { DTOVoucher, Voucher } from "@/services/api/models/Voucher";

const voucherApiUrl = "http://localhost:8071/api/v1.0/admin/vouchers/";

test.describe("Vouchers filters", () => {
  let store = getVouchersScenarioStore(10);

  test.beforeEach(async ({ page }) => {
    store = getVouchersScenarioStore(10);
    await mockPlaywrightCrud<Voucher, DTOVoucher>({
      data: store.list,
      routeUrl: voucherApiUrl,
      page,
      searchResult: store.list[1],
    });
  });

  test("Search by code filters the list", async ({ page }) => {
    await page.goto(PATH_ADMIN.vouchers.list);
    await expect(page.getByRole("heading", { name: "Vouchers" })).toBeVisible();

    // Check all vouchers are visible initially
    await Promise.all(
      store.list.map(async (voucher) => {
        await expect(
          page.getByRole("link", { name: voucher.code }),
        ).toBeVisible();
      }),
    );

    const searchInput = page.getByPlaceholder("Search by code or discount");
    await expect(searchInput).toBeVisible();

    // Type a query matching the chosen searchResult
    const target = store.list[1];
    await searchInput.fill(target.code);

    // Only the target should be visible after debounce + fetch; others may be hidden
    await expect(page.getByRole("link", { name: target.code })).toBeVisible();

    // Some other code should not be visible anymore
    const other =
      store.list[0].code !== target.code
        ? store.list[0].code
        : store.list[2].code;
    await expect(page.getByRole("link", { name: other })).not.toBeVisible();

    // Clear search -> list returns to initial state
    await mockPlaywrightCrud<Voucher, DTOVoucher>({
      data: store.list,
      routeUrl: voucherApiUrl,
      page,
      forceFiltersMode: false,
    });
    await searchInput.fill("");

    // Expect several items again
    await Promise.all(
      store.list.slice(0, 3).map(async (voucher) => {
        await expect(
          page.getByRole("link", { name: voucher.code }),
        ).toBeVisible();
      }),
    );
  });
});
