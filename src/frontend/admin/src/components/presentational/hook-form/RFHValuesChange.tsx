import * as React from "react";
import { PropsWithChildren, useEffect, useState } from "react";
import { useFormContext } from "react-hook-form";
import { useDebouncedCallback } from "use-debounce";
import { FieldValues } from "react-hook-form/dist/types/fields";
import { useRouter } from "next/router";
import { deleteUnusedFilters } from "@/utils/filters";
import { useTranslatableFormContext } from "@/components/presentational/translatable-content/TranslatableForm";

export type RHFValuesChangeProps<T extends FieldValues> = {
  onSubmit: (values: T) => void;
  debounceTime?: number;
  useAnotherValueReference?: boolean;
  formValuesToFilterValues?: (values: T) => any;
  updateUrl?: boolean;
};
export function RHFValuesChange<T extends FieldValues>({
  debounceTime = 800,
  updateUrl = false,
  formValuesToFilterValues,
  useAnotherValueReference = false,
  ...props
}: PropsWithChildren<RHFValuesChangeProps<T>>) {
  const {
    handleSubmit,
    watch,
    trigger,
    formState: { isValid, errors },
  } = useFormContext<T>();
  const translatableFormContext = useTranslatableFormContext();
  const values = watch();
  const router = useRouter();
  const [oldValues, setOldValues] = useState<T>(values);

  const onUpdateUrl = async (newValues: T) => {
    if (!updateUrl) {
      return;
    }
    let filterValues = formValuesToFilterValues?.(newValues) ?? newValues;
    filterValues = { ...deleteUnusedFilters(router.query), ...filterValues };
    await router.push({ query: deleteUnusedFilters(filterValues) });
  };

  const onValuesChange = useDebouncedCallback(() => {
    console.log("IS VALID", isValid, errors);
    if (!isValid) {
      trigger();
      return;
    }
    /**
     * Because with the react hook form, the reference does not change, so if we want to perform a particular behavior
     * with a setState for example, the setState does not trigger a rerender, because the reference has not changed.
     */
    if (useAnotherValueReference) {
      console.log("AA");
      handleSubmit(() => props.onSubmit({ ...values }))();
    } else {
      console.log("BB");
      handleSubmit(props.onSubmit)();
    }

    if (updateUrl) {
      onUpdateUrl({ ...values });
    }
  }, debounceTime);

  useEffect(() => {
    console.log(
      "WEEESSSHHH",
      JSON.stringify(values) !== JSON.stringify(oldValues),
    );
    if (JSON.stringify(values) !== JSON.stringify(oldValues)) {
      setOldValues(values);
      console.log("A", translatableFormContext?.formHasBeenReset);
      if (translatableFormContext?.formHasBeenReset) {
        console.log("A.1");
        translatableFormContext.setFormHasBeenRest(false);
        return;
      }
      console.log("A.2");
      onValuesChange();
    }
  }, [values]);

  return <div>{props.children}</div>;
}
