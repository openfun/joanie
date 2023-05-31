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
];
