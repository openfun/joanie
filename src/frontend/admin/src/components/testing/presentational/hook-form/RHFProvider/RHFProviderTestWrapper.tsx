import * as React from "react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import Box from "@mui/material/Box";
import Grid from "@mui/material/Unstable_Grid2";
import Typography from "@mui/material/Typography";
import {
  RHFProvider,
  RHFProviderProps,
} from "@/components/presentational/hook-form/RHFProvider";
import { RHFTextField } from "@/components/presentational/hook-form/RHFTextField";
import { CustomLink } from "@/components/presentational/link/CustomLink";

type Props = Omit<RHFProviderProps<any>, "methods" | "children"> & {};
export function RHFProviderTestWrapper(props: Props) {
  const [name, setName] = useState("");
  const methods = useForm({
    defaultValues: { name: "" },
  });

  const onSubmit = (values: any) => {
    setName(values.name);
  };

  return (
    <Box padding={4}>
      <Typography data-testid="name-value">Name: {name}</Typography>
      <RHFProvider
        {...props}
        onSubmit={methods.handleSubmit(onSubmit)}
        id="rhf-provider-test"
        methods={methods}
      >
        <Grid container spacing={2}>
          <Grid xs={12}>
            <RHFTextField name="name" label="Name" />
          </Grid>
        </Grid>
      </RHFProvider>
      <CustomLink data-testid="exit-link" href="/form-test">
        Exit
      </CustomLink>
    </Box>
  );
}
