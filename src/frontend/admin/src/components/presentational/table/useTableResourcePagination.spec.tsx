import { act, cleanup, renderHook, waitFor } from "@testing-library/react";
import mockRouter from "next-router-mock";
import { usePaginatedTableResource } from "@/components/presentational/table/usePaginatedTableResource";
import { Organization } from "@/services/api/models/Organization";
import { useOrganizations } from "@/hooks/useOrganizations/useOrganizations";
import { TestingWrapper } from "@/components/testing/TestingWrapper";

describe("usePaginatedTableResource Hook", () => {
  beforeEach(() => {
    mockRouter.query.page = undefined;
    jest.useFakeTimers({
      // Explicitly tell Jest not to affect the "queueMicrotask" calls.
      advanceTimers: true,
      doNotFake: ["queueMicrotask"],
    });
  });

  afterEach(() => {
    cleanup();
    jest.runOnlyPendingTimers();
    jest.useRealTimers();
  });

  it("sets initial values and check states after a success request", async () => {
    const { result } = renderHook(
      () =>
        usePaginatedTableResource<Organization>({
          useResource: useOrganizations,
        }),
      { wrapper: TestingWrapper },
    );

    expect(result.current.tableProps.loading).toBe(true);
    expect(result.current.tableProps.rows.length).toEqual(0);
    expect(result.current.tableProps.rowCount).toEqual(0);
    expect(result.current.meta?.pagination?.count).toEqual(undefined);
    expect(result.current.tableProps.paginationModel).toEqual({
      pageSize: 20,
      page: 0,
    });

    await waitFor(() => {
      expect(result.current.tableProps.loading).toBe(false);
      expect(result.current.states.fetching).toBe(false);
    });
    expect(result.current.tableProps.rows.length).toEqual(10);
    expect(result.current.tableProps.rowCount).toEqual(10);
    expect(result.current.meta?.pagination?.count).toEqual(10);
    expect(result.current.tableProps.paginationModel).toEqual({
      pageSize: 20,
      page: 0,
    });
  });

  it("sets initial values with hook props", async () => {
    const { result } = renderHook(
      () =>
        usePaginatedTableResource<Organization>({
          useResource: useOrganizations,
          initialPage: 2,
          initialItemsPerPage: 15,
        }),
      { wrapper: TestingWrapper },
    );

    expect(result.current.tableProps.paginationModel.page).toBe(2);
    expect(result.current.tableProps.paginationModel.pageSize).toBe(15);
  });

  it("resets current page on onSearch", async () => {
    const { result } = renderHook(
      () =>
        usePaginatedTableResource<Organization>({
          useResource: useOrganizations,
          initialPage: 2,
        }),
      { wrapper: TestingWrapper },
    );

    expect(result.current.tableProps.paginationModel.page).toBe(2);
    expect(result.current.tableProps.paginationModel.pageSize).toBe(20);

    result.current.tableProps.onSearch("Search");
    await act(async () => {
      jest.runOnlyPendingTimers();
    });

    expect(result.current.tableProps.paginationModel.page).toBe(0);
  });
});
