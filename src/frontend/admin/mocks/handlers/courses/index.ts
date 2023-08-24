import { rest } from "msw";
import { buildApiUrl } from "@/services/http/HttpService";
import { coursesRoute } from "@/services/repositories/courses/CoursesRepository";
import { CourseFactory } from "@/services/factories/courses";

export const coursesHandlers = [
  rest.get(buildApiUrl(coursesRoute.getAll()), (req, res, ctx) => {
    return res(ctx.json(CourseFactory(10)));
  }),
  rest.get(buildApiUrl(coursesRoute.get(":id")), (req, res, ctx) => {
    return res(ctx.json(CourseFactory()));
  }),
  rest.options(buildApiUrl(coursesRoute.options), (req, res, ctx) => {
    const result = {
      actions: {
        POST: {
          accesses: {
            child: {
              children: {
                role: {
                  choices: [
                    {
                      value: "owner",
                      display_name: "owner",
                    },
                    {
                      value: "administrator",
                      display_name: "administrator",
                    },
                    {
                      value: "instructor",
                      display_name: "instructor",
                    },
                    {
                      value: "manager",
                      display_name: "manager",
                    },
                  ],
                },
              },
            },
          },
        },
      },
    };
    return res(ctx.json(result));
  }),
];
