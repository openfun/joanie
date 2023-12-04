// eslint-disable-next-line import/no-extraneous-dependencies
import { matchRequestUrl } from "msw";
import { server } from "../../mocks/server";

export function waitForRequest(method: string, url: string) {
  let requestId = "";

  return new Promise((resolve, reject) => {
    server.events.on("request:start", ({ request: req, requestId: toto }) => {
      const matchesMethod = req.method.toLowerCase() === method.toLowerCase();
      // eslint-disable-next-line compat/compat
      const requestUrl = new URL(req.url);
      const matchesUrl = matchRequestUrl(requestUrl, url).matches;

      if (matchesMethod && matchesUrl) {
        requestId = toto;
      }
    });

    server.events.on("request:match", (req) => {
      if (req.requestId === requestId) {
        resolve(req);
      }
    });

    server.events.on("request:unhandled", (req) => {
      if (req.requestId === requestId) {
        const requestUrl = new URL(req.request.url);
        reject(
          new Error(
            `The ${req.request.method} ${requestUrl.href} request was unhandled.`,
          ),
        );
      }
    });
  });
}
