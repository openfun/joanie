import * as React from "react";
import { PropsWithChildren, useEffect } from "react";
import { useFormContext } from "react-hook-form";
import { useDebouncedCallback } from "use-debounce";
import { FieldValues } from "react-hook-form/dist/types/fields";

type Props<T extends FieldValues> = {
  onSubmit: (values: T) => void;
  debounceTime?: number;
};
export function RHFValuesChange<T extends FieldValues>({
  debounceTime = 800,
  ...props
}: PropsWithChildren<Props<T>>) {
  const {
    handleSubmit,
    watch,
    formState: { isDirty, isValid },
  } = useFormContext<T>();
  const values = watch();

  const onValuesChange = useDebouncedCallback(() => {
    if (!isDirty || !isValid) {
      return;
    }

    handleSubmit(props.onSubmit)();
  }, debounceTime);

  useEffect(() => {
    onValuesChange();
  }, [values]);

  return <div>{props.children}</div>;
}
