import { randomNumber } from "@/utils/numbers";

describe("<numbers />", () => {
  it("get random number between 0 and 3", async () => {
    let number = randomNumber(3);
    expect(number).toBeLessThanOrEqual(3);

    number = randomNumber(3);
    expect(number).toBeLessThanOrEqual(3);

    number = randomNumber(3);
    expect(number).toBeLessThanOrEqual(3);

    number = randomNumber(3);
    expect(number).toBeLessThanOrEqual(3);
  });
});
