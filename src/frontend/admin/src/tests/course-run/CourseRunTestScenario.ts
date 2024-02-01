import { faker } from "@faker-js/faker";
import { CourseRunFactory } from "@/services/factories/courses-runs";
import { Course, DTOCourse } from "@/services/api/models/Course";
import { CourseRun, DTOCourseRun } from "@/services/api/models/CourseRun";
import { mockResource } from "@/tests/mockResource";

export const getCourseRunTestScenario = (nbItems: number = 4) => {
  const courseRuns = CourseRunFactory(nbItems);
  const courses: Course[] = [];
  courseRuns.forEach((courseRun) => {
    courses.push(courseRun.course);
  });

  const coursesResource = mockResource<Course, DTOCourse>({
    data: courses,
  });

  const editOrCreate = (payload: DTOCourseRun, courseRunToEdit?: CourseRun) => {
    // return editOrCreateCourseRunTest(payload, courses, courseRunToEdit);
    const { course_id: courseId, id, ...restPayload } = payload;
    const payloadCourse = coursesResource.getResource(courseId);
    const result: CourseRun = {
      ...(courseRunToEdit ?? { id: faker.string.uuid() }),
      ...restPayload,
      course: payloadCourse,
    };

    if (courseRunToEdit) {
      const index = coursesResource.getResourceIndex(courseRunToEdit.id);
      courseRuns[index] = result;
    } else {
      courseRuns.push(result);
    }

    return result;
  };

  return {
    courseRuns,
    courses,
    editOrCreate,
  };
};
