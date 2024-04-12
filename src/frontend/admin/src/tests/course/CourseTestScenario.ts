import { faker } from "@faker-js/faker"; // eslint-disable-next-line import/no-extraneous-dependencies
import { Page } from "@playwright/test";
import { Course, DTOCourse } from "@/services/api/models/Course";
import { CourseFactory } from "@/services/factories/courses";
import {
  DTOOrganization,
  Organization,
} from "@/services/api/models/Organization";
import { User } from "@/services/api/models/User";
import { Product } from "@/services/api/models/Product";
import { mockResource } from "@/tests/mockResource";
import { CourseRun } from "@/services/api/models/CourseRun";
import { catchAllIdRegex } from "@/tests/useResourceHandler";
import { postUpdateOrganization } from "@/tests/organization/OrganizationTestScenario";
import {
  CourseProductRelation,
  DTOCourseProductRelation,
} from "@/services/api/models/Relations";
import { DTOOrderGroup, OrderGroup } from "@/services/api/models/OrderGroup";
import { mockCourseRunsFromCourse } from "@/tests/mocks/course-runs/course-runs-mocks";

export const getCourseScenarioStore = () => {
  const list = CourseFactory(5);
  const organizationList: Organization[] = [];
  const userList: User[] = [];
  const products: Product[] = [];
  const productRelations: CourseProductRelation[] = [];
  const courseRuns: CourseRun[] = [];
  let orderGroups: OrderGroup[] = [];

  list.forEach((course) => {
    course.organizations.forEach((organization) => {
      organizationList.push(organization);
    });
    course.accesses?.forEach((access) => {
      userList.push(access.user);
    });
    course.product_relations?.forEach((relation) => {
      productRelations.push(relation);
      products.push(relation.product);
      organizationList.concat(relation.organizations);
      orderGroups = orderGroups.concat(relation.order_groups);
    });
    course.courses_runs?.forEach((courseRun) => {
      courseRuns.push(courseRun);
    });
  });

  const productResource = mockResource<Product, DTOCourse>({
    data: products,
  });

  const organizationResource = mockResource<Organization, DTOOrganization>({
    data: organizationList,
  });

  const productRelationResource = mockResource<
    CourseProductRelation,
    DTOCourseProductRelation
  >({
    data: productRelations,
  });

  const courseResource = mockResource<Course, DTOCourse>({
    data: list,
  });

  const postProductRelation = (
    payload: DTOCourseProductRelation,
    relation?: CourseProductRelation,
  ) => {
    const course = courseResource.getResource(payload.course_id);
    const product = productResource.getResource(payload.product_id);
    const orgs: Organization[] = [];
    payload.organization_ids.forEach((id) => {
      const organization = organizationResource.getResource(id);
      if (organization) {
        orgs.push(organization);
      }
    });

    let result: CourseProductRelation;
    if (relation) {
      result = {
        ...relation,
        product,
        organizations: orgs,
      };
      const index = productRelationResource.getResourceIndex(relation.id);
      productRelations[index] = result;
    } else {
      result = {
        id: faker.string.uuid(),
        product,
        organizations: orgs,
        order_groups: [],
        can_edit: true,
      };
      productRelations.push(result);
      course.product_relations = [...(course.product_relations ?? []), result];
    }
    return result;
  };

  const postUpdate = (payload: DTOCourse, course?: Course) => {
    const {
      organization_ids: organizationsPayload,
      cover,
      effort,
      ...restPayload
    } = payload;

    const addedOrganizations: Organization[] = [];
    organizationsPayload.forEach((orgId) => {
      addedOrganizations.push(organizationResource.getResource(orgId));
    });

    const index = list.findIndex((item) => item.id === course?.id);

    const effortPayload = effort ? { effort } : {};
    let newCourse: Course;
    if (course && index >= 0) {
      newCourse = {
        ...course,
        ...restPayload,
        organizations: addedOrganizations,
        ...effortPayload,
      };
      list[index] = newCourse;
    } else {
      newCourse = {
        id: faker.string.uuid(),
        ...restPayload,
        organizations: addedOrganizations,
        is_graded: false,
        ...effortPayload,
      };
      list.push(newCourse);
    }
    return newCourse;
  };

  const createOrg = (payload: DTOOrganization) => {
    return postUpdateOrganization(payload, undefined, organizationList);
  };

  return {
    list,
    organizations: organizationList,
    users: userList,
    products,
    courseRuns,
    orderGroups,
    postUpdate,
    createOrg,
    postProductRelation,
    productRelations,
    mockCourseRunsFromCourse,
    mockOrderGroup,
  };
};

export const mockOrderGroup = async (
  page: Page,
  relations: CourseProductRelation[] = [],
  orderGroupList: OrderGroup[] = [],
) => {
  const orderGroupRegex = catchAllIdRegex(
    `http://localhost:8071/api/v1.0/admin/course-product-relations/:uuid/order-groups/`,
    ":uuid",
  );

  const orderGroupUpdateRegex = catchAllIdRegex(
    `http://localhost:8071/api/v1.0/admin/course-product-relations/:uuid/order-groups/:uuid/`,
    ":uuid",
  );

  const orderGroupResource = mockResource<OrderGroup, DTOOrderGroup>({
    data: orderGroupList,
  });

  const relationsResource = mockResource<
    CourseProductRelation,
    DTOCourseProductRelation
  >({
    data: relations,
  });

  const postOrderGroup = (
    payload: DTOOrderGroup,
    relationId: string,
    orderGroupToEdit?: OrderGroup,
  ) => {
    let result: OrderGroup;
    if (orderGroupToEdit) {
      result = {
        ...orderGroupToEdit,
        ...payload,
        nb_available_seats:
          orderGroupToEdit.nb_available_seats +
          (payload.nb_seats - orderGroupToEdit.nb_seats),
      };
      const index = orderGroupResource.getResourceIndex(orderGroupToEdit.id);
      orderGroupList[index] = result;
    } else {
      result = {
        id: faker.string.uuid(),
        ...payload,
        nb_available_seats: payload.nb_seats,
        can_edit: false,
      };
      orderGroupList.push(result);
      const relation = relationsResource.getResource(relationId);
      relation.order_groups = relation.order_groups.concat(result);
    }
    return result;
  };

  await page.unroute(orderGroupRegex);
  await page.route(orderGroupRegex, async (route, request) => {
    const methods = request.method();
    const resultMatch = request.url().match(orderGroupRegex);
    const relationId = resultMatch?.[1] ?? "id";

    if (methods === "POST") {
      const payload: DTOOrderGroup = request.postDataJSON();
      const create = postOrderGroup(payload, relationId);
      await route.fulfill({ json: create });
    }
  });

  await page.unroute(orderGroupUpdateRegex);
  await page.route(orderGroupUpdateRegex, async (route, request) => {
    const methods = request.method();
    const resultMatch = request.url().match(orderGroupUpdateRegex);
    const relationId = resultMatch?.[1] ?? "id";
    const orderGroupId = resultMatch?.[2] ?? "orderGroupId";

    if (methods === "PATCH") {
      const payload: DTOOrderGroup = request.postDataJSON();
      const orderGroup = orderGroupResource.getResource(orderGroupId);
      const update = postOrderGroup(payload, relationId, orderGroup);
      await route.fulfill({ json: update });
    }
    if (methods === "DELETE") {
      const orderGroup = orderGroupResource.deleteResource(orderGroupId);
      await route.fulfill({ json: orderGroup });
    }
  });
};
