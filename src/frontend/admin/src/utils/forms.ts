import { FieldPath } from "react-hook-form/dist/types/path";
import { FieldValues } from "react-hook-form/dist/types/fields";
import { UseFormSetError } from "react-hook-form";
import { ServerSideErrorForm } from "@/types/utils";

export const appendToFormData = (
  key: string,
  value: any,
  formData: FormData = new FormData(),
) => {
  // TODO: Manage FileList
  if (Array.isArray(value)) {
    if (value.length === 0) {
      appendToFormData(key, "", formData);
    } else {
      value.forEach((entity, index) => {
        if (typeof entity === "object" && !(entity instanceof File)) {
          Object.entries(entity).forEach(([key1, value1]) => {
            appendToFormData(`${key}[${index}].${key1}`, value1, formData);
          });
        } else {
          appendToFormData(`${key}[${index}]`, entity, formData);
        }
      });
    }
  } else {
    formData.append(key, value ?? "");
  }
};

export const exportToFormData = (payload: any): FormData => {
  const formData = new FormData();

  Object.entries(payload).forEach(([key, value]) =>
    appendToFormData(key, value, formData),
  );

  return formData;
};

export const genericUpdateFormError = <T extends FieldValues>(
  errors: ServerSideErrorForm<T>,
  setError: UseFormSetError<T>,
) => {
  Object.entries(errors).forEach((entry) => {
    const key: string = entry[0];
    const value: string[] = entry[1] as string[];
    setError(key as FieldPath<T>, {
      type: "custom",
      message: value.join(", "),
    });
  });
};
