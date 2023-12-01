import {
  act,
  cleanup,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { SnackbarProvider } from "notistack";
import { server } from "mocks/server";
import userEvent from "@testing-library/user-event";
import { ProductForm } from "@/components/templates/products/form/ProductForm";
import { TestingWrapper } from "@/components/testing/TestingWrapper";
import { CourseFactory } from "@/services/factories/courses";
import { buildApiUrl } from "@/services/http/HttpService";
import { coursesRoute } from "@/services/repositories/courses/CoursesRepository";
import { CourseRunFactory } from "@/services/factories/courses-runs";
import { organizationRoute } from "@/services/repositories/organization/OrganizationRepository";
import { OrganizationFactory } from "@/services/factories/organizations";
import { waitForRequest } from "@/utils/testing";
import { productRoute } from "@/services/repositories/products/ProductRepository";

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
    jest.useFakeTimers({
      // Explicitly tell Jest not to affect the "queueMicrotask" calls.
      doNotFake: ["queueMicrotask"],
      advanceTimers: true,
    });

    server.use(
      http.get(buildApiUrl(coursesRoute.getAll()), () => {
        return HttpResponse.json([course]);
      }),
      http.get(buildApiUrl(coursesRoute.getCoursesRuns(":id", "")), () => {
        return HttpResponse.json([courseRun]);
      }),
      http.get(buildApiUrl(organizationRoute.getAll()), () => {
        return HttpResponse.json([org]);
      }),
    );
  });

  afterEach(() => {
    cleanup();
    jest.runOnlyPendingTimers();
    jest.useRealTimers();
  });

  it("renders ProductForm without product and select certificate type", async () => {
    const { container } = render(
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

    expect(
      screen.queryByRole("button", {
        name: "Main",
      }),
    ).toBeInTheDocument();

    expect(
      screen.queryByRole("button", { name: "Next" }),
    ).not.toBeInTheDocument();

    const titleInput = screen.getByRole("textbox", { name: "Title" });
    screen.getByRole("combobox", { name: "Type" });
    const description = screen.getByRole("textbox", { name: "Description" });
    screen.getByRole("combobox", { name: "Certificate definition" });

    const instructionTitle = screen.getByRole("heading", {
      name: "Product instructions",
      level: 6,
    });
    screen.getByText("(click to edit)");
    await userEvent.click(instructionTitle);

    expect(screen.queryByText("(click to edit)")).not.toBeInTheDocument();

    const markdownEditorContainer =
      container.getElementsByClassName("w-md-editor");
    expect(markdownEditorContainer.length).toBe(1);
    const markdownEditor: HTMLElement = markdownEditorContainer.item(
      0,
    ) as HTMLElement;
    expect(markdownEditor).not.toBe(null);
    const markdownTextbox = within(markdownEditor).getByRole("textbox");
    await userEvent.type(markdownTextbox, "### Hello");
    expect(markdownTextbox).toHaveValue("### Hello");

    screen.getByRole("heading", { name: "Financial information's" });
    const callToActionInput = screen.getByRole("textbox", {
      name: "Call to action",
    });
    screen.getByRole("spinbutton", { name: "Price" });
    screen.getByRole("combobox", { name: "Price currency" });

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
      jest.runOnlyPendingTimers();
    });

    const r: any = await pendingRequest;
    expect(r.request.url).toEqual(buildApiUrl(productRoute.create));
    await waitFor(() => {
      expect(mockEnqueue).toBeCalled();
    });
  }, 15000);
});
