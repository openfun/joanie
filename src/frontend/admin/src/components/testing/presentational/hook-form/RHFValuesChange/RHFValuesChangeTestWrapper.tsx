import * as React from "react";
import { useForm } from "react-hook-form";
import Box from "@mui/material/Box";
import Grid from "@mui/material/Unstable_Grid2";
import * as Yup from "yup";
import { yupResolver } from "@hookform/resolvers/yup";
import { RHFProvider } from "@/components/presentational/hook-form/RHFProvider";
import { RHFTextField } from "@/components/presentational/hook-form/RHFTextField";
import {
  RHFValuesChange,
  RHFValuesChangeProps,
} from "@/components/presentational/hook-form/RFHValuesChange";
import { RHFSelect } from "@/components/presentational/hook-form/RHFSelect";
import RHFRadioGroup from "@/components/presentational/hook-form/RHFRadioGroup";

type Props = Omit<RHFValuesChangeProps<any>, "children"> & {
  enableSchema?: boolean;
  valuesToFiltersValues?: any;
};
export function RHFValuesChangeTestWrapper({
  enableSchema = false,
  valuesToFiltersValues,
  ...props
}: Props) {
  const RegisterSchema = Yup.object().shape({
    name: Yup.string().required(),
    select: Yup.string().nullable(),
    enable: Yup.mixed().nullable(),
  });

  const methods = useForm({
    defaultValues: { name: "", select: "None", enable: "" },
    resolver: enableSchema ? yupResolver(RegisterSchema) : undefined,
  });

  return (
    <Box padding={4}>
      <RHFProvider
        showSubmit={false}
        onSubmit={methods.handleSubmit(props.onSubmit)}
        id="rhf-values-change-test"
        methods={methods}
      >
        <RHFValuesChange
          {...props}
          updateUrl={true}
          formValuesToFilterValues={() => valuesToFiltersValues ?? undefined}
        >
          <Grid container spacing={2}>
            <Grid xs={12}>
              <RHFTextField name="name" label="Name" />
            </Grid>
            <Grid xs={12}>
              <RHFSelect
                name="select"
                label="Select"
                noneOption={true}
                options={[
                  { label: "First", value: "1" },
                  { label: "Second", value: "2" },
                ]}
              />
            </Grid>
            <Grid xs={12}>
              <RHFRadioGroup
                row
                data-testid="radio-input-enable"
                options={[
                  { label: "None", value: "None" },
                  { label: "True", value: "true" },
                  { label: "False", value: "false" },
                ]}
                label="Enable"
                name="enable"
              />
            </Grid>
          </Grid>
        </RHFValuesChange>
      </RHFProvider>
    </Box>
  );
}
