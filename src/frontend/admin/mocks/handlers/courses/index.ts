import { rest } from "msw";
import { buildApiUrl } from "@/services/http/HttpService";
import { coursesRoute } from "@/services/repositories/courses/CoursesRepository";
import {
  createDummyCourse,
  createDummyCourses,
} from "@/services/factories/courses/courseFactory";

export const coursesHandlers = [
  rest.get(buildApiUrl(coursesRoute.getAll()), (req, res, ctx) => {
    return res(ctx.json(createDummyCourses()));
  }),
  rest.get(buildApiUrl(coursesRoute.get("123")), (req, res, ctx) => {
    return res(ctx.json(createDummyCourse()));
  }),
];
