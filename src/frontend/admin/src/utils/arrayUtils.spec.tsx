import { mergeArrayUnique } from "@/utils/array";

describe("Array Utils", () => {
  it("merge unique", async () => {
    let a = [1, 2, 3];
    let b = [1, 4, 5, 2];
    let result = mergeArrayUnique(a, b);
    expect(result).toEqual([1, 2, 3, 4, 5]);

    a = [1, 2, 3, 4];
    b = [];
    result = mergeArrayUnique(a, b);
    expect(result).toEqual([1, 2, 3, 4]);

    a = [];
    b = [99, 100];
    result = mergeArrayUnique(a, b);
    expect(result).toEqual([99, 100]);

    a = [];
    b = [];
    result = mergeArrayUnique(a, b);
    expect(result).toEqual([]);
  });
});
