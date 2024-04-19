import { Maybe } from "@/types/utils";

export const useFormSubmit = (formEntity: Maybe<any>) => {
  return {
    showSubmit: !formEntity,
    enableAutoSave: !!formEntity,
  };
};
