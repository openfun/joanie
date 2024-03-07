import { PropsWithChildren, useEffect } from "react";
import { useFormContext } from "react-hook-form";
import { useRouter } from "next/router";
import {
  SearchFilterComponentProps,
  useSearchFilterContext,
} from "@/components/presentational/filters/SearchFilters";

type Props = SearchFilterComponentProps;

export function InitializeInputFilters({
  children,
  filterQueryName,
  findFilterValue,
  isFilterContext = false,
  name,
}: PropsWithChildren<Props>) {
  const router = useRouter();
  const filterContext = useSearchFilterContext(isFilterContext);
  const { setValue, resetField } = useFormContext();

  useEffect(() => {
    if (!isFilterContext) {
      return;
    }

    const params = router.query[filterQueryName ?? name];
    if (!params) {
      return;
    }

    findFilterValue?.(Array.isArray(params) ? params : [params])
      .then((result) => {
        setValue(name, result, {
          shouldValidate: true,
          shouldDirty: true,
          shouldTouch: true,
        });
      })
      .catch(() => {
        filterContext?.clearAll();
        resetField(name, { keepTouched: true, keepDirty: true });
      });
  }, []);

  return children;
}
