import { deleteUnusedFilters, getAvailableFilters } from "@/utils/filters";

describe("Filters Utils", () => {
  it("getAvailableFilters", async () => {
    const filters = { page: 1, id: 2, value: 3, state: 4 };
    const result = getAvailableFilters(filters);
    expect(result).toEqual(["value", "state"]);
  });

  it("deleteUnusedFilters", async () => {
    const filters = {
      page: 1,
      id: 2,
      a: "",
      b: null,
      c: undefined,
      d: "none",
      f: "None",
      value: 3,
      state: 4,
    };
    const result = deleteUnusedFilters(filters);
    expect(result).toEqual({ value: 3, state: 4 });
  });
});
