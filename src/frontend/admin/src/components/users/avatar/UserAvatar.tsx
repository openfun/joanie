import * as React from "react";
import { Avatar } from "@mui/material";
import { AvatarProps } from "@mui/material/Avatar/Avatar";

interface Props extends AvatarProps {}

export function UserAvatar(props: Props) {
  return <Avatar alt="Your avatar" src="/images/avatar.jpg" {...props} />;
}
