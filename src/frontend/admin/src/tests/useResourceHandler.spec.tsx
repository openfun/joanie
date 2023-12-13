import { faker } from "@faker-js/faker";
import { catchAllIdRegex } from "@/tests/useResourceHandler";

describe("useRessourceHandler", () => {
  it("catchAllIdRegex", async () => {
    const routeUrl = "/test/:uuid/john/doe/:uuid/";
    const testUrl = `/test/${faker.string.uuid()}/john/doe/${faker.string.uuid()}/`;
    let regex = catchAllIdRegex(routeUrl, ":id");
    expect(regex.test(testUrl)).toEqual(false);

    regex = catchAllIdRegex(routeUrl, ":uuid");
    expect(regex.test(testUrl)).toEqual(true);
    expect(regex.test(`${testUrl}?email=johndoe@yopmail.com`)).toEqual(true);
  });
});
