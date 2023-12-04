import { http, HttpResponse } from "msw";
import { buildApiUrl } from "@/services/http/HttpService";
import { coursesRunsRoute } from "@/services/repositories/courses-runs/CoursesRunsRepository";
import { CourseRunFactory } from "@/services/factories/courses-runs";

export const coursesRunsHandlers = [
  http.get(buildApiUrl(coursesRunsRoute.getAll()), () => {
    return HttpResponse.json(CourseRunFactory(10));
  }),
  http.get(buildApiUrl(coursesRunsRoute.get(":id")), () => {
    return HttpResponse.json(CourseRunFactory());
  }),
  http.options(buildApiUrl(coursesRunsRoute.getAll()), () => {
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
    return HttpResponse.json(result);
  }),
];
