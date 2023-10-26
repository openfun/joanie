import { renderHook, waitFor } from "@testing-library/react";
import { useTableResourcePagination } from "@/components/presentational/table/useTableResourcePagination";
import { Organization } from "@/services/api/models/Organization";
import { useOrganizations } from "@/hooks/useOrganizations/useOrganizations";
import { TestingWrapper } from "@/components/testing/TestingWrapper";

describe("useFetchData Hook", () => {
  it("initial and success state", async () => {
    const { result } = renderHook(
      () =>
        useTableResourcePagination<Organization>({
          useResource: useOrganizations,
        }),
      { wrapper: TestingWrapper },
    );

    expect(result.current.tableProps.loading).toBe(true);
    expect(result.current.tableProps.rows.length).toEqual(0);
    expect(result.current.tableProps.rowCount).toEqual(0);
    expect(result.current.tableProps.paginationModel).toEqual({
      pageSize: 20,
      page: 0,
    });

    await waitFor(() => {
      expect(result.current.tableProps.loading).toBe(false);
      expect(result.current.useResource.states.fetching).toBe(false);
    });
    expect(result.current.tableProps.rows.length).toEqual(10);
    expect(result.current.tableProps.rowCount).toEqual(10);
    expect(result.current.tableProps.paginationModel).toEqual({
      pageSize: 20,
      page: 0,
    });
  });
});
