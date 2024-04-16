import { expect, Locator, Page } from "@playwright/test";
import { Maybe } from "@/types/utils";

const haveClasses = async (locator: Locator, className: string) => {
  // get current classes of element
  const attrClass = await locator.getAttribute("class");
  const elementClasses: string[] = attrClass ? attrClass.split(" ") : [];
  const targetClasses: string[] = className.split(" ");
  // Every class should be present in the current class list
  return targetClasses.every((classItem) => elementClasses.includes(classItem));
};

export async function expectHaveClasses(locator: Locator, className: string) {
  const isValid = await haveClasses(locator, className);
  expect(isValid).toBeTruthy();
}

export async function expectHaveNotClasses(
  locator: Locator,
  className: string,
) {
  const isValid = await haveClasses(locator, className);
  expect(isValid).toBeFalsy();
}

export async function findWithClasses(
  locator: Locator,
  className: string,
  numberOfElementToBeVisible: number = 1,
) {
  const elementsCount = await locator.count();
  const array = [...Array(elementsCount).keys()];
  const result: Locator[] = [];
  await Promise.all(
    array.map(async (number) => {
      const element = locator.nth(number);
      const isValid = await haveClasses(element, className);
      if (isValid) {
        await expect(element).toBeVisible();
        result.push(element);
      }
    }),
  );

  expect(result.length).toEqual(numberOfElementToBeVisible);
}

export const getTestCookie = async (
  page: Page,
  cookieName: string,
): Promise<Maybe<string>> => {
  const cookies = await page.context().cookies();
  const result = cookies.find((cookie) => {
    return cookieName === cookie.name;
  });

  return result?.value ?? undefined;
};

export const formatShortDateTest = async (
  page: Page,
  isoDate: string,
): Promise<string> => {
  const lang = await getTestCookie(page, "django_language");
  return new Intl.DateTimeFormat(lang ?? "en-US", {
    dateStyle: "short",
    timeStyle: "short",
    timeZone: "UTC",
  }).format(new Date(isoDate));
};
