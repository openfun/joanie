import {
  MutateOptions,
  useMutation,
  useQuery,
  useQueryClient,
  UseQueryResult,
} from "@tanstack/react-query";
import { useCallback, useEffect, useMemo, useState } from "react";
import { defineMessages, useIntl } from "react-intl";
import { useSnackbar } from "notistack";
import { ApiResourceInterface, useLocalizedQueryKey } from "./types";
import { Resource, ResourcesQuery, UseResourcesProps } from "./index";
import usePrevious from "@/hooks/usePrevious";
import { REACT_QUERY_SETTINGS } from "@/utils/settings";
import { AddParameters, Maybe } from "@/types/utils";
import { PaginatedResponse } from "@/types/api";
import { noop } from "@/utils";
import { HttpError } from "@/services/http/HttpError";

export const messages = defineMessages({
  errorGet: {
    id: "hooks.useResources.errorGet",
    description:
      "Error message shown to the user when resource fetch request fails.",
    defaultMessage:
      "An error occurred while fetching resources. Please retry later.",
  },
  errorNotFound: {
    id: "hooks.useResources.errorNotFound",
    description: "Error message shown to the user when no resources matches.",
    defaultMessage: "Cannot find the resource.",
  },
  errorUpdate: {
    id: "hooks.useResources.errorUpdate",
    description:
      "Error message shown to the user when resource update request fails.",
    defaultMessage:
      "An error occurred while updating a resource. Please retry later.",
  },
  errorDelete: {
    id: "hooks.useResources.errorDelete",
    description:
      "Error message shown to the user when resource deletion request fails.",
    defaultMessage:
      "An error occurred while deleting a resource. Please retry later.",
  },
  errorCreate: {
    id: "hooks.useResources.errorCreate",
    description:
      "Error message shown to the user when resource creation request fails.",
    defaultMessage:
      "An error occurred while creating a resource. Please retry later.",
  },
  postSuccess: {
    id: "hooks.useResources.postSuccess",
    description:
      "Success message shown to the user when resource was created / updated / deleted",
    defaultMessage: "Operation completed successfully.",
  },
});

type MutateFunc<TApiMethod extends Maybe<(...args: any[]) => any>> =
  AddParameters<
    NonNullable<TApiMethod>,
    [
      options?: MutateOptions<
        Awaited<ReturnType<NonNullable<TApiMethod>>>,
        HttpError
      >,
    ]
  >;

const emptyArray: never[] = [];

/**
 * This hook is a wrapper around `useQuery` and `useMutation` to fetch and mutate resources.
 *
 * @param queryKey - The resource name ( e.g. "todos" )
 * @param apiInterface - A callback that returns the API interface to use for this resource.
 * @param frozenQueryKey - Indicates whether it should do a new API request when the filters change.
 * @param filters - The filters to apply to the API request. Depends on frozenQueryKey.
 * @param session - If true uses useSessionQuery, otherwise useQuery.
 * @param queryOptions - Pass custom options to react-query.
 * @param localized - Is the resource local-dependent ? If so, the query will be invalidated on locale change.
 * @param resourceMessages - Custom messages to use for this resource.
 * @param onMutationSuccess
 */
export const useResourcesRoot = <
  TData extends Resource,
  TResourceQuery extends ResourcesQuery = ResourcesQuery,
  TApiResource extends
    ApiResourceInterface<TData> = ApiResourceInterface<TData>,
>({
  queryKey,
  apiInterface,
  frozenQueryKey,
  filters,
  session,
  queryOptions,
  localized,
  messages: resourceMessages,
  onMutationSuccess,
}: UseResourcesProps<TData, TResourceQuery, TApiResource>) => {
  const snackbar = useSnackbar();
  const queryClient = useQueryClient();
  const [error, setError] = useState<Maybe<string>>();
  const intl = useIntl();

  const actualMessages = useMemo(
    () => ({ ...messages, ...resourceMessages }),
    [resourceMessages],
  );

  const COMMON_QUERY_KEY = frozenQueryKey
    ? [...queryKey]
    : [...queryKey, JSON.stringify(filters)];
  const LOCALIZED_QUERY_KEY = useLocalizedQueryKey(COMMON_QUERY_KEY);
  const QUERY_KEY = localized ? LOCALIZED_QUERY_KEY : COMMON_QUERY_KEY;
  const ACTUAL_QUERY_KEY = QUERY_KEY;

  const api = apiInterface();

  const queryFn: () => Promise<any> = useCallback(
    () => api.get(filters),
    [api, filters],
  );

  const showSuccessMessage = (message?: string) => {
    const str = message ?? intl.formatMessage(messages.postSuccess);
    snackbar.enqueueSnackbar(str, {
      variant: "success",
      preventDuplicate: true,
    });
    updateError(undefined);
  };

  const updateError = (newError: Maybe<string>) => {
    setError(newError);
    if (newError) {
      snackbar.enqueueSnackbar(newError, {
        variant: "error",
        preventDuplicate: true,
      });
    }
  };

  if (session !== usePrevious(session)) {
    throw new Error("session must never change value.");
  }

  let readHandler: UseQueryResult<any, HttpError>;
  // eslint-disable-next-line prefer-const
  readHandler = useQuery({ queryKey: QUERY_KEY, queryFn, ...queryOptions });

  useEffect(() => {
    if (readHandler.error) {
      updateError(intl.formatMessage(actualMessages.errorGet));
    }
  }, [readHandler.error]);

  const invalidate = async () => {
    // Invalidate all queries related to the resource
    await queryClient.invalidateQueries({
      predicate: (query) => {
        return query.queryKey.includes(queryKey[0]);
      },
    });
  };

  const prefetch = async () => {
    await queryClient.prefetchQuery({
      queryKey: ACTUAL_QUERY_KEY,
      queryFn,
      staleTime: session
        ? REACT_QUERY_SETTINGS.staleTimes.sessionItems
        : REACT_QUERY_SETTINGS.staleTimes.default,
    });
  };

  const onSuccess = async () => {
    snackbar.enqueueSnackbar(intl.formatMessage(messages.postSuccess), {
      variant: "success",
      preventDuplicate: true,
    });
    updateError(undefined);
    await invalidate();
    await onMutationSuccess?.(queryClient);
  };

  // const mutation = (
  //   session ? useSessionMutation : useMutation
  // ) as typeof useMutation;
  const mutation = useMutation;

  const writeHandlers = {
    create: api.create
      ? mutation({
          mutationFn: api.create,
          onSuccess,
          onError: () =>
            updateError(intl.formatMessage(actualMessages.errorCreate)),
        })
      : undefined,
    update: api.update
      ? mutation({
          mutationFn: api.update,
          onSuccess,
          onError: () =>
            updateError(intl.formatMessage(actualMessages.errorUpdate)),
        })
      : undefined,
    delete: api.delete
      ? mutation({
          mutationFn: api.delete,
          onSuccess,
          onError: () =>
            updateError(intl.formatMessage(actualMessages.errorDelete)),
        })
      : undefined,
  };

  // We want to keep the same reference to the empty array to avoid potential
  // infinite useEffect calls that use `items` as a dependency.
  const getData = (): {
    items: TData[];
    meta?: { pagination?: Omit<PaginatedResponse<TData>, "results"> };
  } => {
    if (!readHandler.data) {
      return { items: emptyArray };
    }
    // Is it a PaginatedResponse ?
    if (
      typeof readHandler.data === "object" &&
      readHandler.data.hasOwnProperty("results") &&
      readHandler.data.hasOwnProperty("next") &&
      readHandler.data.hasOwnProperty("previous") &&
      readHandler.data.hasOwnProperty("count")
    ) {
      return {
        items: readHandler.data.results,
        meta: {
          pagination: {
            count: readHandler.data.count,
            next: readHandler.data.next,
            previous: readHandler.data.previous,
          },
        },
      };
    }

    // If a single resource has been returned by API, we wrap it in an array
    if (!Array.isArray(readHandler.data)) {
      return { items: [readHandler.data] };
    }

    return { items: readHandler.data };
  };

  const { items, meta } = getData();

  return {
    items,
    meta,
    methods: {
      mutation,
      invalidate,
      prefetch,
      refetch: readHandler.refetch,
      create: (writeHandlers.create
        ? writeHandlers.create.mutate
        : noop) as unknown as MutateFunc<TApiResource["create"]>,
      update: (writeHandlers.update
        ? writeHandlers.update.mutate
        : noop) as unknown as MutateFunc<TApiResource["update"]>,
      delete: (writeHandlers.delete
        ? writeHandlers.delete.mutate
        : noop) as unknown as MutateFunc<TApiResource["delete"]>,
      setError: updateError,
      showSuccessMessage,
      onSuccess,
    },
    states: {
      fetching: readHandler.fetchStatus === "fetching",
      creating: writeHandlers.create?.isPending,
      deleting: writeHandlers.delete?.isPending,
      updating: writeHandlers.update?.isPending,
      isLoading: [...Object.values(writeHandlers), readHandler].some(
        (value) => value?.isPending,
      ),
      isFetched: readHandler.isFetched,
      error,
    },
  };
};
