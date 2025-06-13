import { faker } from "@faker-js/faker";
import { Page } from "@playwright/test";
import { Course, DTOCourse } from "@/services/api/models/Course";
import { CourseFactory } from "@/services/factories/courses";
import {
  DTOOrganization,
  Organization,
} from "@/services/api/models/Organization";
import { User } from "@/services/api/models/User";
import { BaseProduct } from "@/services/api/models/Product";
import { mockResource } from "@/tests/mockResource";
import { CourseRun } from "@/services/api/models/CourseRun";
import { catchAllIdRegex } from "@/tests/useResourceHandler";
import { postUpdateOrganization } from "@/tests/organization/OrganizationTestScenario";
import {
  CourseProductRelation,
  DTOCourseProductRelation,
} from "@/services/api/models/Relations";
import { DTOOfferRule, OfferRule } from "@/services/api/models/OfferRule";
import { mockCourseRunsFromCourse } from "@/tests/mocks/course-runs/course-runs-mocks";
import { Discount, DTODiscount } from "@/services/api/models/Discount";
import { DiscountFactory } from "@/services/factories/discounts";

export const getCourseScenarioStore = () => {
  const list = CourseFactory(5);
  const organizationList: Organization[] = [];
  const userList: User[] = [];
  const products: BaseProduct[] = [];
  const productRelations: CourseProductRelation[] = [];
  const courseRuns: CourseRun[] = [];
  let offerRules: OfferRule[] = [];
  const discounts: Discount[] = DiscountFactory(3);

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
      offerRules = offerRules.concat(relation.offer_rules);
    });
    course.courses_runs?.forEach((courseRun) => {
      courseRuns.push(courseRun);
    });
  });

  const productResource = mockResource<BaseProduct, DTOCourse>({
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
      const { product_relations: pr, ...restCourse } = course;
      result = {
        id: faker.string.uuid(),
        product,
        course: restCourse,
        organizations: orgs,
        offer_rules: [],
        can_edit: true,
      };
      productRelations.push(result);
      course.product_relations = [...(pr ?? []), result];
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

  const createDiscount = (payload: DTODiscount) => {
    let discount = DiscountFactory();
    discount = {
      ...discount,
      ...payload,
    };
    discounts.push(discount);
    return discount;
  };

  return {
    list,
    organizations: organizationList,
    users: userList,
    products,
    courseRuns,
    offerRules,
    discounts,
    postUpdate,
    createOrg,
    postProductRelation,
    productRelations,
    mockCourseRunsFromCourse,
    mockOfferRule,
    createDiscount,
  };
};

export const mockOfferRule = async (
  page: Page,
  relations: CourseProductRelation[] = [],
  offerRuleList: OfferRule[] = [],
  discounts: Discount[] = [],
) => {
  const offerRuleRegex = catchAllIdRegex(
    `http://localhost:8071/api/v1.0/admin/course-product-relations/:uuid/offer-rules/`,
    ":uuid",
  );

  const offerRuleUpdateRegex = catchAllIdRegex(
    `http://localhost:8071/api/v1.0/admin/course-product-relations/:uuid/offer-rules/:uuid/`,
    ":uuid",
  );

  const offerRuleResource = mockResource<OfferRule, DTOOfferRule>({
    data: offerRuleList,
  });

  const relationsResource = mockResource<
    CourseProductRelation,
    DTOCourseProductRelation
  >({
    data: relations,
  });

  const discountResource = mockResource<Discount, DTODiscount>({
    data: discounts,
  });

  const postOfferRule = (
    payload: DTOOfferRule,
    relationId: string,
    offerRuleToEdit?: OfferRule,
  ) => {
    let result: OfferRule;
    if (offerRuleToEdit) {
      result = {
        ...offerRuleToEdit,
        ...payload,
        nb_available_seats:
          (offerRuleToEdit.nb_available_seats ?? 0) +
          ((payload.nb_seats ?? 0) - (offerRuleToEdit.nb_seats ?? 0)),
      };
      const index = offerRuleResource.getResourceIndex(offerRuleToEdit.id);
      offerRuleList[index] = result;
    } else {
      result = {
        id: faker.string.uuid(),
        ...payload,
        description: payload.description ?? null,
        nb_seats: payload.nb_seats ?? null,
        nb_available_seats: payload.nb_seats ?? null,
        start: payload.start ?? null,
        end: payload.end ?? null,
        can_edit: false,
        discount: null,
      };
      offerRuleList.push(result);
      const relation = relationsResource.getResource(relationId);
      relation.offer_rules = relation.offer_rules.concat(result);
    }

    if (payload.discount_id) {
      const discount = discountResource.getResource(payload.discount_id);
      if (discount) {
        result.discount = discount;
      }
    }

    return result;
  };

  await page.unroute(offerRuleRegex);
  await page.route(offerRuleRegex, async (route, request) => {
    const methods = request.method();
    const resultMatch = request.url().match(offerRuleRegex);
    const relationId = resultMatch?.[1] ?? "id";

    if (methods === "POST") {
      const payload: DTOOfferRule = request.postDataJSON();
      const create = postOfferRule(payload, relationId);
      await route.fulfill({ json: create });
    }
  });

  await page.unroute(offerRuleUpdateRegex);
  await page.route(offerRuleUpdateRegex, async (route, request) => {
    const methods = request.method();
    const resultMatch = request.url().match(offerRuleUpdateRegex);
    const relationId = resultMatch?.[1] ?? "id";
    const offerRuleId = resultMatch?.[2] ?? "offerRuleId";

    if (methods === "PATCH") {
      const payload: DTOOfferRule = request.postDataJSON();
      const offerRule = offerRuleResource.getResource(offerRuleId);
      const update = postOfferRule(payload, relationId, offerRule);
      await route.fulfill({ json: update });
    }
    if (methods === "DELETE") {
      const offerRule = offerRuleResource.deleteResource(offerRuleId);
      await route.fulfill({ json: offerRule });
    }
  });
};
