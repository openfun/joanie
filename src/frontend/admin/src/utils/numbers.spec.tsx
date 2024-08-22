import { randomNumber, toDigitString } from "@/utils/numbers";

describe("utils/numbers", () => {
  describe("randomNumber", () => {
    it("get random number between 0 and 3", () => {
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

  describe("toDigitString", () => {
    it("converts number to digit string", () => {
      let digit = toDigitString(9);
      expect(digit).toBe("09");

      digit = toDigitString(10);
      expect(digit).toBe("10");

      digit = toDigitString(1_000_001);
      expect(digit).toBe("1000001");
    });
  });
});
