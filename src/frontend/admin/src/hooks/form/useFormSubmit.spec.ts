import { renderHook } from "@testing-library/react";
import { useFormSubmit } from "@/hooks/form/useFormSubmit";

describe("useFormSubmit", () => {
  it("if entity is undefined", async () => {
    const entity = undefined;
    const { result } = renderHook(() => useFormSubmit(entity));
    expect(result.current.showSubmit).toEqual(true);
    expect(result.current.enableAutoSave).toEqual(false);
  });

  it("if entity is not undefined", async () => {
    const entity = { a: 1 };
    const { result } = renderHook(() => useFormSubmit(entity));
    expect(result.current.showSubmit).toEqual(false);
    expect(result.current.enableAutoSave).toEqual(true);
  });
});
