import * as React from "react";
import { useForm } from "react-hook-form";
import Grid from "@mui/material/Unstable_Grid2";
import {
  SearchFilterProps,
  SearchFilters,
} from "@/components/presentational/filters/SearchFilters";
import { RHFProvider } from "@/components/presentational/hook-form/RHFProvider";
import { RHFValuesChange } from "@/components/presentational/hook-form/RFHValuesChange";
import RHFRadioGroup from "@/components/presentational/hook-form/RHFRadioGroup";
import { RHFSelect } from "@/components/presentational/hook-form/RHFSelect";
import RHFAutocomplete from "@/components/presentational/hook-form/RHFAutocomplete";

type Props = SearchFilterProps & {};
export function SearchFiltersWrapperTest(props: Props) {
  const methods = useForm({
    defaultValues: {
      enable: "none",
      language: "",
      user: null,
    },
  });

  return (
    <SearchFilters
      {...props}
      renderContent={() => (
        <RHFProvider id="test-filter-form" showSubmit={false} methods={methods}>
          <RHFValuesChange
            debounceTime={200}
            useAnotherValueReference={true}
            onSubmit={() => {}}
          >
            <Grid container mt={2} spacing={2}>
              <Grid xs={12}>
                <RHFRadioGroup
                  row
                  isFilterContext={true}
                  name="enable"
                  label="Enable"
                  options={[
                    { label: "None", value: "none" },
                    { label: "Yes", value: "yes" },
                    { label: "No", value: "no" },
                  ]}
                />
              </Grid>
              <Grid xs={12}>
                <RHFSelect
                  isFilterContext={true}
                  name="language"
                  label="Language"
                  noneOption={true}
                  options={[
                    { label: "French", value: "fr" },
                    { label: "English", value: "en" },
                  ]}
                />
              </Grid>
              <Grid xs={12}>
                <RHFAutocomplete
                  data-testid="autocomplete-test"
                  findFilterValue={async (values) => values}
                  isFilterContext={true}
                  name="user"
                  label="User"
                  options={["JohnDoe", "SachaSmith"]}
                />
              </Grid>
            </Grid>
          </RHFValuesChange>
        </RHFProvider>
      )}
    />
  );
}
