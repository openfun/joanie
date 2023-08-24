import * as React from "react";
import { useForm } from "react-hook-form";
import * as Yup from "yup";
import { yupResolver } from "@hookform/resolvers/yup";
import Grid2 from "@mui/material/Unstable_Grid2";
import Button from "@mui/material/Button";
import Box from "@mui/material/Box";
import { defineMessages, useIntl } from "react-intl";
import { RHFProvider } from "@/components/presentational/hook-form/RHFProvider";
import { UserSearch } from "@/components/templates/users/inputs/search/UserSearch";
import {
  RHFSelect,
  SelectOption,
} from "@/components/presentational/hook-form/RHFSelect";
import { User } from "@/services/api/models/User";
import { Nullable, ToFormValues } from "@/types/utils";
import { commonTranslations } from "@/translations/common/commonTranslations";

const messages = defineMessages({
  roleLabel: {
    id: "components.template.accesses.list.AddUserAccess.roleLabel",
    defaultMessage: "Role",
    description: "Role label for the access select",
  },
  userLabel: {
    id: "components.template.accesses.list.AddUserAccess.userLabel",
    defaultMessage: "User",
    description: "User label for the user input",
  },
});

export type AddUserAccessFromValues = ToFormValues<{
  user: Nullable<User>;
  role: string;
}>;

type Props = {
  allAccesses: SelectOption[];
  defaultRole: string;
  onAdd: (user: User, role: string) => void;
};
export function AddUserAccess(props: Props) {
  const intl = useIntl();
  const Schema = Yup.object().shape({
    user: Yup.mixed<User>().required().nullable(),
    role: Yup.string().required(),
  });

  const methods = useForm<AddUserAccessFromValues>({
    resolver: yupResolver(Schema),
    reValidateMode: "onSubmit",
    mode: "onSubmit",
    defaultValues: {
      user: null,
      role: props.defaultRole,
    },
  });

  const onSubmit = (values: AddUserAccessFromValues) => {
    if (!values.user) {
      methods.setError("user", { type: "required" });
    } else {
      props.onAdd(values.user, values.role);
    }
  };

  return (
    <RHFProvider
      showSubmit={false}
      methods={methods}
      onSubmit={methods.handleSubmit(onSubmit)}
    >
      <Grid2 container spacing={2}>
        <Grid2 xs={12} md={5}>
          <UserSearch
            name="user"
            label={intl.formatMessage(messages.userLabel)}
            size="small"
          />
        </Grid2>
        <Grid2 xs={12} md={5}>
          <RHFSelect
            size="small"
            options={props.allAccesses}
            name="role"
            data-testid="select-role"
            label={intl.formatMessage(messages.roleLabel)}
          />
        </Grid2>
        <Grid2 xs={12} md={2}>
          <Box display="flex" justifyContent="center" alignItems="center">
            <Button fullWidth type="submit" variant="contained">
              {intl.formatMessage(commonTranslations.add)}
            </Button>
          </Box>
        </Grid2>
      </Grid2>
    </RHFProvider>
  );
}
