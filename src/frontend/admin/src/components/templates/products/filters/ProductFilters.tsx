import * as React from "react";
import * as Yup from "yup";
import { useForm } from "react-hook-form";
import { yupResolver } from "@hookform/resolvers/yup";
import Grid from "@mui/material/Unstable_Grid2";
import { defineMessages, useIntl } from "react-intl";
import {
  MandatorySearchFilterProps,
  SearchFilters,
} from "@/components/presentational/filters/SearchFilters";
import { RHFProvider } from "@/components/presentational/hook-form/RHFProvider";
import { RHFValuesChange } from "@/components/presentational/hook-form/RFHValuesChange";
import { RHFProductType } from "@/components/templates/products/inputs/RHFProductType";
import { ProductResourceQuery } from "@/hooks/useProducts/useProducts";

const messages = defineMessages({
  searchPlaceholder: {
    id: "components.templates.products.filters.ProductFilers.searchPlaceholder",
    description: "Text for the search input placeholder",
    defaultMessage: "Search by title",
  },
});

type Props = MandatorySearchFilterProps & {
  onFilter: (values: ProductResourceQuery) => void;
};

export function ProductFilers({ onFilter, ...searchFilterProps }: Props) {
  const intl = useIntl();
  const getDefaultValues = () => {
    return {
      type: "",
    };
  };
  const RegisterSchema = Yup.object().shape({
    type: Yup.string().nullable(),
  });

  const methods = useForm({
    resolver: yupResolver(RegisterSchema),
    defaultValues: getDefaultValues() as any, // To not trigger type validation for default value
  });

  return (
    <SearchFilters
      {...searchFilterProps}
      searchInputPlaceholder={intl.formatMessage(messages.searchPlaceholder)}
      renderContent={() => (
        <RHFProvider
          id="certificate-definition-filter-form"
          showSubmit={false}
          methods={methods}
        >
          <RHFValuesChange
            debounceTime={200}
            useAnotherValueReference={true}
            onSubmit={onFilter}
          >
            <Grid container mt={2} spacing={2}>
              <Grid xs={12}>
                <RHFProductType isFilterContext={true} name="type" />
              </Grid>
            </Grid>
          </RHFValuesChange>
        </RHFProvider>
      )}
    />
  );
}
