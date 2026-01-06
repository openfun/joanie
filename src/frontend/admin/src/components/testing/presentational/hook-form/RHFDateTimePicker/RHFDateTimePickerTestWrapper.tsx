import * as React from "react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import Grid from "@mui/material/Grid2";
import {
  RHFProvider,
  RHFProviderProps,
} from "@/components/presentational/hook-form/RHFProvider";
import { Nullable } from "@/types/utils";
import { RHFDateTimePicker } from "@/components/presentational/hook-form/RHFDateTimePicker";
import { TestingWrapper } from "@/components/testing/TestingWrapper";

type Props = Omit<RHFProviderProps<any>, "methods" | "children"> & {};
export function RHFDateTimePickerTestWrapper(props: Props) {
  const [date, setDate] = useState<Nullable<Date>>(null);
  const methods = useForm({
    defaultValues: { end: null },
  });

  const onSubmit = (values: any) => {
    setDate(values.name);
  };

  return (
    <TestingWrapper>
      <Box padding={4}>
        <Typography data-testid="date-value">
          Date: {date?.toISOString()}
        </Typography>
        <RHFProvider
          {...props}
          onSubmit={methods.handleSubmit(onSubmit)}
          id="rhf-provider-test"
          methods={methods}
        >
          <Grid container spacing={2}>
            <Grid size={12}>
              <RHFDateTimePicker name="end" label="End" />
            </Grid>
          </Grid>
        </RHFProvider>
      </Box>
    </TestingWrapper>
  );
}
