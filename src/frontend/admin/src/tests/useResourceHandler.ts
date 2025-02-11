import { Page } from "@playwright/test";
import { mockResource, WithId } from "@/tests/mockResource";
import { DEFAULT_PAGE_SIZE } from "@/utils/constants";

type Props<T extends WithId, Payload> = {
  routeUrl: string;
  page: Page;
  searchTimeout?: number;
  forceFiltersMode?: boolean;
  updateCallback?: (payload: Payload, item?: T) => T;
  createCallback?: (payload: Payload) => T;
  optionsResult?: any;
  searchResult?: T | T[];
  getByIdResult?: T;
  data: T[];
};

export const getUrlCatchSearchParamsRegex = (routeUrl: string): RegExp => {
  return new RegExp(`^${routeUrl}(\\?.*)*$`);
};

export const getUrlCatchIdRegex = (routeUrl: string): RegExp => {
  return new RegExp(
    `^${routeUrl}([0-9a-fA-F]{8}\\b-[0-9a-fA-F]{4}\\b-[0-9a-fA-F]{4}\\b-[0-9a-fA-F]{4}\\b-[0-9a-fA-F]{12})/(\\?.*)*$`,
  );
};

export const catchAllIdRegex = (
  routeUrl: string,
  keyToReplace: string,
): RegExp => {
  const pattern = routeUrl.replaceAll(
    keyToReplace,
    `([0-9a-fA-F]{8}\\b-[0-9a-fA-F]{4}\\b-[0-9a-fA-F]{4}\\b-[0-9a-fA-F]{4}\\b-[0-9a-fA-F]{12})`,
  );

  return new RegExp(`^${pattern}(\\?.*)*$`);
};

export const mockPlaywrightCrud = async <T extends WithId, Payload>({
  routeUrl,
  searchTimeout = 0,
  forceFiltersMode = false,
  page,
  ...props
}: Props<T, Payload>) => {
  const resources = mockResource<T, Payload>({
    data: props.data,
    updateCallback: props.updateCallback,
    createCallback: props.createCallback,
  });

  const queryParamsRegex = getUrlCatchSearchParamsRegex(routeUrl);

  const catchIdRegex = getUrlCatchIdRegex(routeUrl);

  await page.unroute(queryParamsRegex);
  await page.route(queryParamsRegex, async (route, request) => {
    const methods = request.method();

    if (methods === "OPTIONS" && props.optionsResult) {
      await route.fulfill({ json: props.optionsResult });
    }

    if (methods === "GET") {
      const url = new URL(request.url());
      const query = url.searchParams.get("query");

      let result = [resources.data[0]];
      if (props.searchResult) {
        result = Array.isArray(props.searchResult)
          ? props.searchResult
          : [props.searchResult];
      }
      if ((query === null || query === "") && !forceFiltersMode) {
        result = [...resources.data];
      }

      let ordering = url.searchParams.get("ordering");
      if (ordering) {
        let order = "asc";
        if (ordering.startsWith("-")) {
          order = "desc";
          ordering = ordering.replace("-", "");
        }

        result = result.sort((a, b) => {
          if (order === "asc") {
            // @ts-ignore
            // Type null cannot be used as an index type. lol
            return a[ordering] > b[ordering] ? 1 : -1;
          }
          // @ts-ignore
          // Type null cannot be used as an index type.
          return a[ordering] < b[ordering] ? 1 : -1;
        });
      }

      setTimeout(async () => {
        const pageNumber = parseInt(url.searchParams.get("page") ?? "1", 10);
        const count = result.length;
        const index =
          pageNumber === 1 ? 0 : (pageNumber - 1) * DEFAULT_PAGE_SIZE;
        const listResult =
          count <= DEFAULT_PAGE_SIZE
            ? result
            : result.splice(index, DEFAULT_PAGE_SIZE);

        const list = {
          count,
          next: null,
          previous: null,
          results: listResult,
        };
        await route.fulfill({ json: list });
      }, searchTimeout);
    }

    if (props.createCallback && methods === "POST") {
      const payload: Payload = request.postDataJSON();
      const create = props.createCallback(payload);
      await route.fulfill({ json: create });
    }
  });

  await page.unroute(catchIdRegex);
  await page.route(catchIdRegex, async (route, request) => {
    const methods = request.method();
    const resultMatch = request.url().match(catchIdRegex);
    const id = resultMatch?.[1] ?? "id";
    if (methods === "GET") {
      const result = id ? resources.getResource(id) : props.getByIdResult;
      await route.fulfill({ json: result });
    }

    if (props.updateCallback && methods === "PATCH") {
      const payload: Payload = request.postDataJSON();
      const update = resources.updateResource(id, payload);
      await route.fulfill({ json: update });
    }

    if (methods === "DELETE") {
      const deleteItem = resources.deleteResource(id);
      await route.fulfill({ json: deleteItem });
    }
  });
};
