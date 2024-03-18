import * as React from "react";
import { ReactNode, useState } from "react";
import Tabs from "@mui/material/Tabs";
import Tab from "@mui/material/Tab";
import Box from "@mui/material/Box";
import Stack from "@mui/material/Stack";
import Alert from "@mui/material/Alert";

export type TabValue = {
  label: string;
  component: ReactNode;
  show?: boolean;
  tabInfo?: string;
};

type Props = {
  id: string;
  tabs: TabValue[];
};

export function TabsComponent({ tabs, id }: Props) {
  const [currentTabValue, setCurrentTabValue] = useState(0);
  const currentTab = tabs[currentTabValue];
  return (
    <>
      <Box sx={{ borderBottom: 1, mb: 1, borderColor: "divider" }}>
        <Tabs
          value={currentTabValue}
          onChange={(v, newValue) => setCurrentTabValue(newValue)}
        >
          {tabs.map((tab, index) => {
            if (tab.show !== undefined && !tab.show) {
              return;
            }
            return (
              <Tab
                key={tab.label}
                label={tab.label}
                value={index}
                {...a11yProps(index, id)}
              />
            );
          })}
        </Tabs>
      </Box>
      <Stack p={3} spacing={2}>
        <>
          {currentTab.tabInfo && (
            <Alert severity="info">{currentTab.tabInfo}</Alert>
          )}
          {(currentTab.show ?? true) && currentTab.component}
        </>
      </Stack>
    </>
  );
}

function a11yProps(index: number, id: string) {
  return {
    id: `${id}-${index}`,
    "aria-controls": `${id}panel-${index}`,
  };
}
