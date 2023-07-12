import * as React from "react";
import { PropsWithChildren } from "react";
import Box from "@mui/material/Box";
import { grey } from "@mui/material/colors";
import Image from "next/image";
import logo from "../../../public/images/logo/logo-fun.svg";
import { SimpleCard } from "@/components/presentational/card/SimpleCard";

export function AuthLayout(props: PropsWithChildren) {
  return (
    <Box
      display="flex"
      justifyContent="center"
      alignItems="center"
      height="100%"
      bgcolor={grey[50]}
    >
      <Box width="100%" maxWidth={480}>
        <SimpleCard>
          <Box
            flexDirection="column"
            padding={3}
            display="flex"
            justifyContent="center"
            alignItems="center"
          >
            <Box mb={3}>
              <Image
                src={logo}
                width={150}
                alt="France Université Numérique logo"
              />
            </Box>
            {props.children}
          </Box>
        </SimpleCard>
      </Box>
    </Box>
  );
}
