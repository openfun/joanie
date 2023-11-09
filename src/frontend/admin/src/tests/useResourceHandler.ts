import { Page } from "@playwright/test";
import { useMockResource, WithId } from "@/tests/useMockResource";

type Props<T extends WithId, Payload> = {
  routeUrl: string;
  page: Page;
  updateCallback?: (payload: Payload, item?: T) => T;
  createCallback?: (payload: Payload) => T;
  searchResult?: T;
  getByIdResult?: T;
  data: T[];
};

export const mockPlaywrightCrud = async <T extends WithId, Payload>({
  routeUrl,
  page,
  ...props
}: Props<T, Payload>) => {
  // eslint-disable-next-line react-hooks/rules-of-hooks
  const mockResource = useMockResource<T, Payload>({
    data: props.data,
    updateCallback: props.updateCallback,
    createCallback: props.createCallback,
  });

  const queryParamsRegex = new RegExp(`^${routeUrl}(\\?.*)*$`);

  const catchIdRegex = new RegExp(
    `^${routeUrl}([0-9a-fA-F]{8}\\b-[0-9a-fA-F]{4}\\b-[0-9a-fA-F]{4}\\b-[0-9a-fA-F]{4}\\b-[0-9a-fA-F]{12})/(\\?.*)*$`,
  );

  await page.unroute(queryParamsRegex);
  await page.route(queryParamsRegex, async (route, request) => {
    const methods = request.method();

    if (methods === "GET") {
      const url = new URL(request.url());
      const query = url.searchParams.get("query");

      let result = [props.searchResult ?? mockResource.data[0]];
      if (query === null || query === "") {
        result = mockResource.data;
      }

      setTimeout(async () => {
        await route.fulfill({ json: result });
      }, 150);
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
      const result = id ? mockResource.getResource(id) : props.getByIdResult;
      await route.fulfill({ json: result });
    }

    if (props.updateCallback && methods === "POST") {
      const payload: Payload = request.postDataJSON();
      const update = mockResource.updateResource(id, payload);
      await route.fulfill({ json: update });
    }

    if (methods === "DELETE") {
      const deleteItem = mockResource.deleteResource(id);
      await route.fulfill({ json: deleteItem });
    }
  });
};
