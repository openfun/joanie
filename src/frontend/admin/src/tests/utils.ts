import { expect, Locator } from "@playwright/test";

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
