import { act, renderHook } from "@testing-library/react";
import { useList } from "@/hooks/useList/useList";

describe("useList hook", () => {
  it("renders useList hook and test all methods", async () => {
    const { result } = renderHook(() => useList([1, 2, 3, 4, 5]));
    expect(result.current.items).toEqual([1, 2, 3, 4, 5]);

    act(() => {
      result.current.removeAt(0);
    });
    expect(result.current.items).toEqual([2, 3, 4, 5]);

    act(() => {
      result.current.insertAt(0, 9);
    });
    expect(result.current.items).toEqual([9, 2, 3, 4, 5]);

    act(() => {
      result.current.updateAt(0, 12);
    });
    expect(result.current.items).toEqual([12, 2, 3, 4, 5]);

    act(() => {
      result.current.push(90);
    });
    expect(result.current.items).toEqual([12, 2, 3, 4, 5, 90]);

    act(() => {
      result.current.set([13]);
    });
    expect(result.current.items).toEqual([13]);
  });
});
