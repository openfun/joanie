import { Page } from "@playwright/test";

export const delay = (ms: number) =>
  new Promise((resolve) => setTimeout(resolve, ms));

export const closeAllNotification = async (page: Page) => {
  const allNotifications = await page.getByTestId("close-notification").all();
  await Promise.all(
    allNotifications.reverse().map(async () => {
      const re = await page.getByTestId("close-notification").all();
      await re[0].click();
      await delay(200);
    }),
  );
};
