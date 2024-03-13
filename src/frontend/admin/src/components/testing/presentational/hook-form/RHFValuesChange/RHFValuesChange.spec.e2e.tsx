import { expect, test } from "@playwright/experimental-ct-react";
import mockRouter from "next-router-mock";
import { HooksConfig } from "../../../../../../playwright";
import { RHFValuesChangeTestWrapper } from "@/components/testing/presentational/hook-form/RHFValuesChange/RHFValuesChangeTestWrapper";
import { PlaywrightCustomRouter } from "@/components/testing/PlaywrightCustomRouter";
import { delay } from "@/components/testing/utils";

test.describe("<RHFValuesChange/>", () => {
  test("check that the url changes at the same time as the form", async ({
    mount,
    page,
  }) => {
    const router = mockRouter;
    let routerHasChange = false;
    mockRouter.events.on("routeChangeStart", () => {
      routerHasChange = true;
    });
    let values = null;
    const component = await mount<HooksConfig>(
      <PlaywrightCustomRouter router={router}>
        <RHFValuesChangeTestWrapper
          debounceTime={20}
          onSubmit={(newValues) => {
            values = newValues;
          }}
        />
      </PlaywrightCustomRouter>,
      { hooksConfig: { customRouting: true } },
    );
    expect(values).toEqual(null);
    await component.getByLabel("Name", { exact: true }).fill("Doe");
    await component.getByLabel("Select", { exact: true }).click();
    await page.getByRole("option", { name: "First" }).click();
    await component
      .getByTestId("radio-input-enable")
      .getByLabel("True")
      .click();

    await delay(50);
    expect(routerHasChange).toEqual(true);
    expect(router.asPath).toEqual("/?name=Doe&select=1&enable=true");
    await component
      .getByTestId("radio-input-enable")
      .getByLabel("None")
      .click();
    await delay(25);
    expect(router.asPath).toEqual("/?name=Doe&select=1");
  });

  test("Check that the submit function is called at the right time without form validation", async ({
    mount,
  }) => {
    const router = mockRouter;
    let values = null;
    const component = await mount<HooksConfig>(
      <PlaywrightCustomRouter router={router}>
        <RHFValuesChangeTestWrapper
          debounceTime={200}
          onSubmit={(newValues) => {
            values = newValues;
          }}
        />
      </PlaywrightCustomRouter>,
      { hooksConfig: { customRouting: true } },
    );
    expect(values).toEqual(null);
    await component.getByLabel("Name", { exact: true }).fill("Doe");
    await component.click();
    await component.getByLabel("Name", { exact: true }).fill("");
    expect(values).toEqual(null);
    await delay(220);
    await component.getByLabel("Name", { exact: true }).fill("John");
    await delay(220);
    expect(values).toEqual({ enable: "", name: "John", select: "None" });
  });

  test("Check that the submit function is called at the right time with form validation", async ({
    mount,
    page,
  }) => {
    const router = mockRouter;
    let values = null;
    const component = await mount<HooksConfig>(
      <PlaywrightCustomRouter router={router}>
        <RHFValuesChangeTestWrapper
          debounceTime={100}
          enableSchema={true}
          onSubmit={(newValues) => {
            values = newValues;
          }}
        />
      </PlaywrightCustomRouter>,
      { hooksConfig: { customRouting: true } },
    );
    expect(values).toEqual(null);
    await component.getByLabel("Select", { exact: true }).click();
    await page.getByRole("option", { name: "First" }).click();
    await delay(120);
    expect(values).toEqual(null);
    await component
      .getByTestId("radio-input-enable")
      .getByLabel("True")
      .click();
    await delay(120);
    expect(values).toEqual(null);
    await component.getByLabel("Name", { exact: true }).fill("Doe");
    await delay(120);
    expect(values).toEqual({ enable: "true", name: "Doe", select: "1" });
  });

  test("Check url when form change with formValuesToFiltersValues props", async ({
    mount,
  }) => {
    const router = mockRouter;
    let values = null;
    const component = await mount<HooksConfig>(
      <PlaywrightCustomRouter router={router}>
        <RHFValuesChangeTestWrapper
          debounceTime={100}
          valuesToFiltersValues={{ a: "1", b: "2" }}
          onSubmit={(newValues) => {
            values = newValues;
          }}
        />
      </PlaywrightCustomRouter>,
      { hooksConfig: { customRouting: true } },
    );
    expect(values).toEqual(null);
    expect(router.asPath).toEqual("/");
    await component.getByLabel("Name", { exact: true }).fill("Doe");
    await component.click();
    await delay(120);
    expect(router.asPath).toEqual("/?a=1&b=2");
  });
  test("Check debounceTime", async ({ mount }) => {
    const router = mockRouter;
    let values = null;
    const component = await mount<HooksConfig>(
      <PlaywrightCustomRouter router={router}>
        <RHFValuesChangeTestWrapper
          debounceTime={400}
          onSubmit={(newValues) => {
            values = newValues;
          }}
        />
      </PlaywrightCustomRouter>,
      { hooksConfig: { customRouting: true } },
    );
    expect(values).toEqual(null);
    await component.getByLabel("Name", { exact: true }).fill("John");
    await component.click();
    expect(values).toEqual(null);
    await delay(200);
    expect(values).toEqual(null);
    await delay(240);
    expect(values).toEqual({ enable: "", name: "John", select: "None" });
  });
});
