import * as React from "react";
import {
  PropsWithChildren,
  ReactNode,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import InputAdornment from "@mui/material/InputAdornment";
import CircularProgress from "@mui/material/CircularProgress";
import SearchOutlined from "@mui/icons-material/SearchOutlined";
import TextField from "@mui/material/TextField";
import { useDebouncedCallback } from "use-debounce";
import { FileDownload, FilterList } from "@mui/icons-material";
import Chip from "@mui/material/Chip";
import Stack from "@mui/material/Stack";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import CloseIcon from "@mui/icons-material/Close";
import { defineMessages, FormattedMessage, useIntl } from "react-intl";
import Alert from "@mui/material/Alert";
import { useRouter } from "next/router";
import { useModal } from "@/components/presentational/modal/useModal";
import { CustomModal } from "@/components/presentational/modal/Modal";
import { Maybe } from "@/types/utils";
import { getAvailableFilters } from "@/utils/filters";

const messages = defineMessages({
  filtersLabelButton: {
    id: "components.presentational.filters.searchFilters.filtersLabelButton",
    defaultMessage: "Filters",
    description: "Label for the filters button",
  },
  exportLabelButton: {
    id: "components.presentational.filters.searchFilters.exportLabelButton",
    defaultMessage: "Export",
    description: "Label for the export button",
  },
  clear: {
    id: "components.presentational.filters.searchFilters.clear",
    defaultMessage: "Clear",
    description: "Label for the clear filters button",
  },
  filtersModalTitle: {
    id: "components.presentational.filters.searchFilters.filtersModalTitle",
    defaultMessage: "Add filters",
    description: "Label for the filter modal title",
  },
  filtersModalInfo: {
    id: "components.presentational.filters.searchFilters.filtersModalInfo",
    defaultMessage:
      'In this part, you can add filters to filter entities based on different parameters. On a multiple choice filter, an "OR" is applied',
    description: "Label for the filter modal alert info",
  },
  searchPlaceholder: {
    id: "components.presentational.filters.searchFilters.searchPlaceholder",
    defaultMessage: "Search...",
    description: "Label for the search input",
  },
});

type FilterChip = {
  name: string;
  filterUrlName?: string;
  label: string;
  value: string;
  onDelete: (name: string) => void;
};

export type MandatorySearchFilterProps = {
  searchInputPlaceholder?: string;
  onSearch?: (term: string) => void;
  loading?: boolean;
};

export type SearchFilterProps = MandatorySearchFilterProps & {
  renderContent?: (
    addChip: (chip: FilterChip) => void,
    removeChip: (chipName: string) => void,
  ) => ReactNode;
  export?: () => void;
};

export function SearchFilters(props: PropsWithChildren<SearchFilterProps>) {
  const router = useRouter();
  const intl = useIntl();
  const modal = useModal();
  const [filtersLoading, setFiltersLoading] = useState(
    getAvailableFilters(router.query).length > 0,
  );
  const [chips, setChips] = useState<FilterChip[]>([]);

  const onChangeSearchInput = useDebouncedCallback((term: string) => {
    props.onSearch?.(term);
  });

  const addChip = (newChip: FilterChip) => {
    setChips((oldValue) => {
      const newChips = [...oldValue];
      const index = newChips.findIndex((chip) => {
        return chip.name === newChip.name;
      });
      if (index < 0) {
        newChips.push(newChip);
      } else {
        newChips[index] = newChip;
      }
      return newChips;
    });
  };

  const deleteChip = (chip: FilterChip, index: number): void => {
    const newChips = [...chips];
    newChips.splice(index, 1);
    setChips(newChips);
    chip.onDelete(chip.name);
  };

  const onRemoveChip = (name: string): void => {
    const newChips = [...chips];
    const index = newChips.findIndex((chip) => {
      return chip.name === name;
    });
    if (index < 0) {
      return;
    }
    newChips.splice(index, 1);
    setChips(newChips);
  };

  const clearAll = () => {
    chips.forEach((chip) => {
      chip.onDelete(chip.name);
    });
    setChips([]);
    setFiltersLoading(false);
  };

  const providerValue = useMemo(() => {
    return { addChip, removeChip: onRemoveChip, clearAll };
  }, [chips, addChip, onRemoveChip, clearAll]);

  useEffect(() => {
    if (!filtersLoading) {
      return;
    }

    const filters = getAvailableFilters(router.query);
    const allChipsName = chips.map((el) => el.filterUrlName ?? el.name);
    const diff = filters.filter((el) => !allChipsName.includes(el));
    setFiltersLoading(diff.length > 0);
  }, [chips]);

  return (
    <SearchFilterContext.Provider value={providerValue}>
      <div>
        <Box display="flex" alignItems="center">
          <TextField
            margin="none"
            autoComplete="off"
            defaultValue=""
            onChange={(event) => onChangeSearchInput(event.target.value)}
            fullWidth
            placeholder={
              props.searchInputPlaceholder ??
              intl.formatMessage(messages.searchPlaceholder)
            }
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  {props.loading ? (
                    <CircularProgress size="19px" />
                  ) : (
                    <SearchOutlined />
                  )}
                </InputAdornment>
              ),
            }}
          />
          {props.renderContent && (
            <Button
              sx={{ ml: 2 }}
              startIcon={<FilterList />}
              onClick={modal.handleOpen}
            >
              <FormattedMessage {...messages.filtersLabelButton} />
            </Button>
          )}
          {props.export && (
            <Button
              sx={{ ml: 2 }}
              startIcon={<FileDownload />}
              onClick={() => {
                if (props.export) {
                  props.export();
                }
              }}
            >
              <FormattedMessage {...messages.exportLabelButton} />
            </Button>
          )}
        </Box>
        {props.renderContent && (
          <Box display="flex" alignItems="center">
            <CustomModal
              keepMounted={true}
              fullWidth={true}
              maxWidth="md"
              title={intl.formatMessage(messages.filtersModalTitle)}
              {...modal}
            >
              <Stack>
                <Alert severity="info">
                  <FormattedMessage {...messages.filtersModalInfo} />
                </Alert>
                <Box>{props.renderContent(addChip, onRemoveChip)}</Box>
              </Stack>
            </CustomModal>
            {(filtersLoading || chips.length > 0) && (
              <Stack
                sx={{ p: "8px 16px 0 16px", width: "100%" }}
                direction="row"
                alignItems="center"
                spacing={1}
                flexWrap="wrap"
              >
                {filtersLoading && (
                  <Box padding={0.5}>
                    <CircularProgress size={22} />
                  </Box>
                )}
                {!filtersLoading &&
                  chips.map((chip, index) => (
                    <Chip
                      key={chip.name}
                      label={`${chip.label}: ${chip.value}`}
                      color="secondary"
                      variant="outlined"
                      size="small"
                      onDelete={() => deleteChip(chip, index)}
                    />
                  ))}
                {!filtersLoading && (
                  <Button
                    size="small"
                    endIcon={<CloseIcon fontSize="small" />}
                    onClick={clearAll}
                  >
                    <FormattedMessage {...messages.clear} />
                  </Button>
                )}
              </Stack>
            )}
          </Box>
        )}
      </div>
    </SearchFilterContext.Provider>
  );
}

export type SearchFilterComponentProps = {
  name: string;
  isFilterContext?: boolean;
  filterQueryName?: string;
  findFilterValue?: (values: string[]) => Promise<any | any[]>;
};

export interface SearchFilterContextInterface {
  clearAll: () => void;
  removeChip: (name: string) => void;
  addChip: (chip: FilterChip) => void;
}

export const SearchFilterContext =
  React.createContext<Maybe<SearchFilterContextInterface>>(undefined);

export const useSearchFilterContext = (enable: boolean = false) => {
  const searchFilterContext = useContext(SearchFilterContext);

  if (!enable) {
    return null;
  }

  if (!searchFilterContext) {
    throw new Error(
      `useSearchFilterContext must be used within a SearchFilterContext`,
    );
  }

  return searchFilterContext;
};
