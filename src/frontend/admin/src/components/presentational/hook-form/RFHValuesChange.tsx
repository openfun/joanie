import * as React from "react";
import { PropsWithChildren, useEffect, useState } from "react";
import { useFormContext } from "react-hook-form";
import { useDebouncedCallback } from "use-debounce";
import { FieldValues } from "react-hook-form/dist/types/fields";
import { useRouter } from "next/router";
import { deleteUnusedFilters } from "@/utils/filters";

type Props<T extends FieldValues> = {
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
}: PropsWithChildren<Props<T>>) {
  const {
    handleSubmit,
    watch,
    formState: { isValid },
  } = useFormContext<T>();
  const values = watch();
  const router = useRouter();
  const [oldValues, setOldValues] = useState<T>();

  const onUpdateUrl = (newValues: T) => {
    if (!updateUrl) {
      return;
    }
    let filterValues = formValuesToFilterValues?.(newValues) ?? newValues;
    filterValues = { ...deleteUnusedFilters(router.query), ...filterValues };
    router.push({ query: deleteUnusedFilters(filterValues) }, undefined, {
      shallow: true,
    });
  };

  const onValuesChange = useDebouncedCallback(() => {
    if (!isValid) {
      return;
    }

    /**
     * Because with the react hook form, the reference does not change, so if we want to perform a particular behavior
     * with a setState for example, the setState does not trigger a rerender, because the reference has not changed.
     */
    if (useAnotherValueReference) {
      handleSubmit(() => props.onSubmit({ ...values }))();
    } else {
      handleSubmit(props.onSubmit)();
    }

    if (updateUrl) {
      onUpdateUrl({ ...values });
    }
  }, debounceTime);

  useEffect(() => {
    if (JSON.stringify(values) !== JSON.stringify(oldValues)) {
      setOldValues(values);
      onValuesChange();
    }
  }, [values]);

  return <div>{props.children}</div>;
}
