import { rest } from "msw";
import { buildApiUrl } from "@/services/http/HttpService";
import { coursesRunsRoute } from "@/services/repositories/courses-runs/CoursesRunsRepository";
import {
  createDummyCourseRun,
  createDummyCoursesRuns,
} from "@/services/factories/courses-runs/coursesRunsFactory";

export const coursesRunsHandlers = [
  rest.get(buildApiUrl(coursesRunsRoute.getAll()), (req, res, ctx) => {
    return res(ctx.json(createDummyCoursesRuns()));
  }),
  rest.get(buildApiUrl(coursesRunsRoute.get(":id")), (req, res, ctx) => {
    return res(ctx.json(createDummyCourseRun()));
  }),
];
