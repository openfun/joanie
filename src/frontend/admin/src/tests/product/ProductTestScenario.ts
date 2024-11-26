import { faker } from "@faker-js/faker";
// eslint-disable-next-line import/no-extraneous-dependencies
import { Page } from "@playwright/test";
import { ProductFactory } from "@/services/factories/product";
import { Course, DTOCourse } from "@/services/api/models/Course";
import { Organization } from "@/services/api/models/Organization";
import { CourseRun, DTOCourseRun } from "@/services/api/models/CourseRun";
import {
  DTOProduct,
  DTOProductCertification,
  Product,
} from "@/services/api/models/Product";
import { CertificateDefinition } from "@/services/api/models/CertificateDefinition";
import { catchAllIdRegex } from "@/tests/useResourceHandler";
import { mockResource } from "@/tests/mockResource";
import {
  DTOProductTargetCourseRelation,
  ProductTargetCourseRelation,
} from "@/services/api/models/ProductTargetCourseRelation";
import { ContractDefinition } from "@/services/api/models/ContractDefinition";
import { DTOTeacher, Teacher } from "@/services/api/models/Teacher";
import { DTOSkill, Skill } from "@/services/api/models/Skill";

type ProductStore = {
  products: Product[];
  certificateDefinitions: CertificateDefinition[];
  contractsDefinitions: ContractDefinition[];
  courses: Course[];
  skills: Skill[];
  teachers: Teacher[];
  targetCourses: ProductTargetCourseRelation[];
  organizations: Organization[];
  courseRuns: CourseRun[];
  postUpdate: (payload: DTOProduct, item?: Product) => Product;
  updateOrCreateTeacher: (payload: DTOTeacher, item?: Teacher) => Teacher;
  updateOrCreateSkill: (payload: DTOSkill, item?: Skill) => Skill;
};

export const getProductScenarioStore = (): ProductStore => {
  const products = ProductFactory(5);
  const certificateDefinitions = products.map((product) => {
    return product.certificate_definition!;
  });

  const contractsDefinitions = products.map((product) => {
    return product.contract_definition!;
  });
  const skills = products.map((product) => product.skills).flat();
  const teachers = products.map((product) => product.teachers).flat();

  const courses: Course[] = [];
  const organizations: Organization[] = [];
  const courseRuns: CourseRun[] = [];
  const targetCourses: ProductTargetCourseRelation[] = [];

  products.forEach((product) => {
    product.target_courses?.forEach((value) => {
      targetCourses.push(value);
      courses.push(value.course);
      value.course.courses_runs?.forEach((courseRun) =>
        courseRuns.push(courseRun),
      );
      value.course_runs.forEach((courseRun) => {
        courseRuns.push(courseRun);
      });
    });
  });

  function postUpdateMainInformation(
    payload: DTOProduct,
    item?: Product,
  ): Product {
    const { contract_definition: newContractDefinition, ...restPayload } =
      payload;

    const contractDef = contractsDefinitions.find(
      (contractDefinition) => contractDefinition.id === newContractDefinition,
    );

    let newProduct: Product;
    if (item) {
      newProduct = {
        ...item,
        ...restPayload,
        contract_definition: contractDef ?? item.contract_definition,
      };
    } else {
      newProduct = {
        id: faker.string.uuid(),
        ...restPayload,
        contract_definition: contractDef ?? null,
        certificate_definition: null,
        certification_level: null,
        teachers: [],
        skills: [],
      };
    }

    return newProduct;
  }

  function postUpdateCertificateInformation(
    payload: DTOProductCertification,
    item: Product,
  ): Product {
    const newCertificateDefinition =
      certificateDefinitions.find(
        (definition) => definition.id === payload.certificate_definition,
      ) ?? null;

    const newSkills = skills.filter(({ id }) => payload.skills.includes(id));
    const newTeachers = teachers.filter(({ id }) =>
      payload.teachers.includes(id),
    );

    return {
      ...item,
      ...payload,
      certificate_definition: newCertificateDefinition,
      skills: newSkills,
      teachers: newTeachers,
    };
  }

  function isDTOProduct(
    payload: DTOProduct | DTOProductCertification,
  ): payload is DTOProduct {
    return payload.hasOwnProperty("title");
  }

  function postUpdate(payload: DTOProduct, item?: Product): Product;
  function postUpdate(payload: DTOProductCertification, item: Product): Product;
  function postUpdate(
    payload: DTOProduct | DTOProductCertification,
    item?: Product,
  ) {
    let newProduct;
    if (isDTOProduct(payload)) {
      newProduct = postUpdateMainInformation(payload, item);
    } else {
      newProduct = postUpdateCertificateInformation(payload, item!);
    }
    products.push(newProduct);
    return newProduct;
  }

  function updateOrCreateTeacher(payload: DTOTeacher, item?: Teacher): Teacher {
    return {
      id: item?.id ?? faker.string.uuid(),
      ...item,
      ...payload,
    };
  }

  function updateOrCreateSkill(payload: DTOSkill, item?: Skill): Skill {
    return {
      id: item?.id ?? faker.string.uuid(),
      ...item,
      ...payload,
    };
  }

  return {
    products,
    certificateDefinitions,
    contractsDefinitions,
    skills,
    teachers,
    courses,
    organizations,
    courseRuns,
    targetCourses,
    postUpdate,
    updateOrCreateTeacher,
    updateOrCreateSkill,
  };
};

export const mockTargetCourses = async (
  page: Page,
  targetCourses: ProductTargetCourseRelation[] = [],
  products: Product[] = [],
  courses: Course[] = [],
  courseRuns: CourseRun[] = [],
) => {
  const orderGroupRegex = catchAllIdRegex(
    `http://localhost:8071/api/v1.0/admin/products/:uuid/target-courses/`,
    ":uuid",
  );

  const orderGroupUpdateRegex = catchAllIdRegex(
    `http://localhost:8071/api/v1.0/admin/products/:uuid/target-courses/:uuid/`,
    ":uuid",
  );

  const productResources = mockResource<Product, DTOProduct>({
    data: products,
  });

  const courseResources = mockResource<Course, DTOCourse>({
    data: courses,
  });

  const courseRunResources = mockResource<CourseRun, DTOCourseRun>({
    data: courseRuns,
  });

  const targetCourseResources = mockResource<
    ProductTargetCourseRelation,
    DTOProductTargetCourseRelation
  >({
    data: targetCourses,
  });

  const editOrCreateTargetCourse = (
    payload: DTOProductTargetCourseRelation,
    productId: string,
    targetCourseToEdit?: ProductTargetCourseRelation,
  ) => {
    const {
      course: courseId,
      course_runs: courseRunIds,
      ...restPayload
    } = payload;

    const courseFromPayload = courseResources.getResource(courseId);
    const courseRunsFromPayload =
      courseRunIds?.map((courseRunId) =>
        courseRunResources.getResource(courseRunId),
      ) ?? [];

    const result: ProductTargetCourseRelation = {
      ...(targetCourseToEdit ?? { id: faker.string.uuid() }),
      ...restPayload,
      course: courseFromPayload,
      course_runs: courseRunsFromPayload,
    };

    if (targetCourseToEdit) {
      const index = targetCourseResources.getResourceIndex(
        targetCourseToEdit.id,
      );
      targetCourses[index] = result;
    } else {
      const product = productResources.getResource(productId);
      targetCourses.push(result);
      if (product.target_courses) {
        product.target_courses.push(result);
      } else {
        product.target_courses = [result];
      }
    }
    return result;
  };

  await page.unroute(orderGroupRegex);
  await page.route(orderGroupRegex, async (route, request) => {
    const methods = request.method();
    const resultMatch = request.url().match(orderGroupRegex);
    const productId = resultMatch?.[1] ?? "id";

    if (methods === "POST") {
      const payload: DTOProductTargetCourseRelation = request.postDataJSON();
      const create = editOrCreateTargetCourse(payload, productId);
      await route.fulfill({ json: create });
    }
  });

  await page.unroute(orderGroupUpdateRegex);
  await page.route(orderGroupUpdateRegex, async (route, request) => {
    const methods = request.method();
    const resultMatch = request.url().match(orderGroupUpdateRegex);
    const productId = resultMatch?.[1] ?? "productId";
    const targetCourseId = resultMatch?.[2] ?? "targetCourseId";

    if (methods === "PATCH") {
      const payload: DTOProductTargetCourseRelation = request.postDataJSON();
      const targetCourse = targetCourseResources.getResource(targetCourseId);
      const update = editOrCreateTargetCourse(payload, productId, targetCourse);
      await route.fulfill({ json: update });
    }
  });
};
