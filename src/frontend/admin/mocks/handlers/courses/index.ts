import { http, HttpResponse } from "msw";
import { buildApiUrl } from "@/services/http/HttpService";
import { coursesRoute } from "@/services/repositories/courses/CoursesRepository";
import { CourseFactory } from "@/services/factories/courses";
import { CourseRunFactory } from "@/services/factories/courses-runs";

export const coursesHandlers = [
  http.get(buildApiUrl(coursesRoute.getAll()), () => {
    return HttpResponse.json(CourseFactory(10));
  }),
  http.get(buildApiUrl(coursesRoute.get(":id")), () => {
    return HttpResponse.json(CourseFactory());
  }),
  http.get(buildApiUrl(coursesRoute.getCoursesRuns(":id", "")), () => {
    return HttpResponse.json(CourseRunFactory(2));
  }),
  http.options(buildApiUrl(coursesRoute.options), () => {
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
    return HttpResponse.json(result);
  }),
];
