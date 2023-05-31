import { rest } from "msw";
import { buildApiUrl } from "@/services/http/HttpService";
import { coursesRunsRoute } from "@/services/repositories/courses-runs/CoursesRunsRepository";
import { CourseRunFactory } from "@/services/factories/courses-runs";

export const coursesRunsHandlers = [
  rest.get(buildApiUrl(coursesRunsRoute.getAll()), (req, res, ctx) => {
    return res(ctx.json(CourseRunFactory(10)));
  }),
  rest.get(buildApiUrl(coursesRunsRoute.get(":id")), (req, res, ctx) => {
    return res(ctx.json(CourseRunFactory()));
  }),
  rest.options(buildApiUrl(coursesRunsRoute.getAll()), (req, res, ctx) => {
    const result = {
      actions: {
        POST: {
          languages: {
            choices: [
              { value: "fr", display_name: "Français" },
              { value: "en", display_name: "English" },
            ],
          },
        },
      },
    };
    return res(ctx.json(result));
  }),
];
