import { act, render, screen, waitFor } from "@testing-library/react";
import { rest } from "msw";
import userEvent from "@testing-library/user-event";
import { SnackbarProvider } from "notistack";
import { server } from "../../../../../mocks/server";
import { ProductForm } from "@/components/templates/products/form/ProductForm";
import { TestingWrapper } from "@/components/testing/TestingWrapper";
import { CourseFactory } from "@/services/factories/courses";
import { buildApiUrl } from "@/services/http/HttpService";
import { coursesRoute } from "@/services/repositories/courses/CoursesRepository";
import { CourseRunFactory } from "@/services/factories/courses-runs";
import { organizationRoute } from "@/services/repositories/organization/OrganizationRepository";
import { OrganizationFactory } from "@/services/factories/organizations";
import { ProductFactory } from "@/services/factories/product";
import { productRoute } from "@/services/repositories/products/ProductRepository";
import { waitForRequest } from "@/utils/testing";

const course = CourseFactory();
course.title = "Testing";
const courseRun = CourseRunFactory();
courseRun.title = "course";
const org = OrganizationFactory();
org.title = "fun";

const mockEnqueue = jest.fn();
jest.mock("notistack", () => ({
  ...jest.requireActual("notistack"),
  useSnackbar: () => {
    return {
      enqueueSnackbar: mockEnqueue,
    };
  },
}));

describe("<ProductForm/>", () => {
  beforeEach(() => {
    server.use(
      rest.get(buildApiUrl(coursesRoute.getAll()), (req, res, ctx) => {
        return res(ctx.json([course]));
      }),
      rest.get(
        buildApiUrl(coursesRoute.getCoursesRuns(":id", "")),
        (req, res, ctx) => {
          return res(ctx.json([courseRun]));
        },
      ),
      rest.get(buildApiUrl(organizationRoute.getAll()), (req, res, ctx) => {
        return res(ctx.json([org]));
      }),
    );
  });

  it("renders ProductForm without product and select certificate type", async () => {
    jest.useFakeTimers({ advanceTimers: true });
    render(
      <SnackbarProvider>
        <ProductForm />
      </SnackbarProvider>,
      { wrapper: TestingWrapper },
    );

    // 2 types of product
    const credential = await screen.findByRole("heading", {
      level: 6,
      name: "Microcredential",
    });

    screen.getByRole("heading", { name: "Certificate", level: 6 });
    await userEvent.click(credential);

    // 3 wizard steps title
    await screen.findByText("Main");

    expect(
      screen.queryByRole("button", { name: "Next" }),
    ).not.toBeInTheDocument();

    // Test Main Form
    screen.getByRole("heading", { name: "Main information's" });
    const titleInput = screen.getByRole("textbox", { name: "Title" });
    screen.getByRole("button", { name: "Type credential" });
    const description = screen.getByRole("textbox", { name: "Description" });
    screen.getByRole("combobox", { name: "Certificate definition" });

    screen.getByRole("heading", { name: "Financial information's" });
    const callToActionInput = screen.getByRole("textbox", {
      name: "Call to action",
    });
    screen.getByRole("spinbutton", { name: "Price" });
    screen.getByRole("button", { name: "Price currency Euro" });

    await userEvent.type(callToActionInput, "Buy");
    expect(callToActionInput).toHaveValue("Buy");

    await userEvent.type(titleInput, "Product one");
    expect(titleInput).toHaveValue("Product one");

    await userEvent.type(description, "description");
    expect(description).toHaveValue("description");
    const pendingRequest = waitForRequest(
      "POST",
      buildApiUrl(productRoute.create),
    );
    await act(async () => {
      jest.advanceTimersByTime(900);
    });

    const request = await pendingRequest;
    expect(request.url.toString()).toEqual(buildApiUrl(productRoute.create));
    await waitFor(() => {
      expect(mockEnqueue).toBeCalled();
    });
  }, 10000);

  it("renders ProductForm and test target course part", async () => {
    const product = ProductFactory();
    product.target_courses = [];
    render(
      <SnackbarProvider>
        <ProductForm product={product} />
      </SnackbarProvider>,
      { wrapper: TestingWrapper },
    );

    // Buttons Back and Next
    const nextButton = await screen.findByRole("button", { name: "Next" });

    const titleInput = screen.getByRole("textbox", { name: "Title" });

    const callToActionInput = screen.getByRole("textbox", {
      name: "Call to action",
    });

    expect(callToActionInput).toHaveValue(product.call_to_action);
    expect(titleInput).toHaveValue(product.title);
    await userEvent.click(nextButton);

    // Test target_courses section
    await screen.findByText(
      "No target course has been added yet. Click the button to add",
    );

    screen.getByRole("heading", { name: "Product target courses" });
    const addTargetCourseButton = screen.getByRole("button", {
      name: "Add target course",
    });
    await userEvent.click(addTargetCourseButton);
    screen.getByText(
      "In this form, you can choose a course to integrate it into the product as well as the associated course runs.",
    );

    const courseSearch = screen.getByRole("combobox", {
      name: "Course search",
    });

    await userEvent.type(courseSearch, "Test");
    const val = await screen.findByRole("option", { name: "Testing" });

    await userEvent.click(val);
    const checkboxLabel = await screen.findByText(
      "Choose specific course-runs",
    );

    expect(
      screen.queryByRole("combobox", {
        name: "Search course run",
      }),
    ).not.toBeInTheDocument();

    await userEvent.click(checkboxLabel);
    const courseRunSearch = screen.getByRole("combobox", {
      name: "Search course run",
    });

    await userEvent.type(courseRunSearch, "course");
    const courseResult = await screen.findByRole("option", { name: "course" });
    await userEvent.click(courseResult);

    screen.getByText("course");
  }, 10000);
});
