import React, { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import Box from "@mui/material/Box";
import CircularProgress from "@mui/material/CircularProgress";
import { useTheme } from "@mui/material/styles";
import { Maybe } from "@/types/utils";

const MDEditor = dynamic(() => import("@uiw/react-md-editor"), { ssr: false });

type Props = {
  value: string;
  onChange: (markdown: Maybe<string>) => void;
};

export function MarkdownComponent(props: Props) {
  const theme = useTheme();
  const [markdownCommands, setMarkdownCommands] =
    useState<typeof import("@uiw/react-md-editor").commands>();

  useEffect(() => {
    // We must import it dynamically to load this module
    // only in a browser context (not ssr).
    import("@uiw/react-md-editor").then((module) => {
      setMarkdownCommands(module.commands);
    });
  }, []);

  if (!markdownCommands) {
    return (
      <Box
        height={200}
        display="flex"
        justifyContent="center"
        alignItems="center"
      >
        <CircularProgress />
      </Box>
    );
  }

  const {
    bold,
    italic,
    strikethrough,
    hr,
    link,
    quote,
    code,
    codeBlock,
    image,

    unorderedListCommand,
    orderedListCommand,
    checkedListCommand,
  } = markdownCommands;

  return (
    <MDEditor
      data-testid="md-editor"
      autoFocus={false}
      height={300}
      data-color-mode={theme.palette.mode}
      commands={[
        bold,
        italic,
        strikethrough,
        hr,
        markdownCommands.group(
          [
            markdownCommands.title3,
            markdownCommands.title4,
            markdownCommands.title5,
            markdownCommands.title6,
          ],
          {
            name: "title",
            groupName: "title",
            buttonProps: { "aria-label": "Insert title" },
          },
        ),
        markdownCommands.divider,
        link,
        quote,
        code,
        codeBlock,
        image,
        markdownCommands.divider,
        unorderedListCommand,
        orderedListCommand,
        checkedListCommand,
      ]}
      {...props}
    />
  );
}
