import { useCallback, useEffect, useRef, useState } from "react";

interface Page<T> {
  items: T[];
  page: number;
  pages: number;
}

interface State<T> {
  load: (page: number, signal: AbortSignal) => Promise<Page<T>>;
  items: T[];
  page: number;
  pages: number;
  loading: boolean;
  loadingMore: boolean;
  error?: Error;
}

const emptyState = <T,>(
  load: State<T>["load"],
  loading: boolean,
): State<T> => ({
  load,
  items: [],
  page: 0,
  pages: 0,
  loading,
  loadingMore: false,
});

/** Loads one page at a time, retaining prior pages and rejecting stale results. */
export function usePageResource<T extends { id: string }>(
  load: (page: number, signal: AbortSignal) => Promise<Page<T>>,
  enabled = true,
) {
  const [state, setState] = useState(() => emptyState(load, true));
  const stateRef = useRef(state);
  const controllerRef = useRef<AbortController | undefined>(undefined);

  const update = useCallback((next: State<T>) => {
    stateRef.current = next;
    setState(next);
  }, []);

  const request = useCallback(
    async (pageNumber: number, signal: AbortSignal) => {
      const previous = stateRef.current;
      const firstPage = pageNumber === 1;
      update({
        ...(previous.load === load
          ? previous
          : emptyState(load, false)),
        load,
        loading: firstPage,
        loadingMore: !firstPage,
        error: undefined,
      });
      try {
        const result = await load(pageNumber, signal);
        if (signal.aborted || stateRef.current.load !== load)
          return;
        const current = stateRef.current;
        const items = firstPage ? result.items : [...current.items, ...result.items];
        update({
          ...current,
          items: [...new Map(items.map((item) => [item.id, item])).values()],
          page: result.page,
          pages: result.pages,
          loading: false,
          loadingMore: false,
        });
      } catch (error) {
        if (signal.aborted || stateRef.current.load !== load) return;
        const current = stateRef.current;
        update({
          ...current,
          loading: false,
          loadingMore: false,
          error: error instanceof Error ? error : new Error(String(error)),
        });
      }
    },
    [load, update],
  );

  useEffect(() => {
    const controller = new AbortController();
    controllerRef.current = controller;
    const previous = stateRef.current;
    const sameQuery = previous.load === load;
    if (
      enabled &&
      !(sameQuery && (previous.page > 0 || previous.error))
    ) {
      update(emptyState(load, true));
      void request(1, controller.signal);
    }
    return () => {
      controller.abort();
      if (controllerRef.current === controller) {
        controllerRef.current = undefined;
        const current = stateRef.current;
        if (current.load === load && current.loadingMore)
          update({ ...current, loadingMore: false });
      }
    };
  }, [enabled, load, request, update]);

  const loadNext = useCallback(() => {
    const current = stateRef.current;
    const controller = controllerRef.current;
    if (
      !enabled ||
      !controller ||
      current.load !== load ||
      current.loading ||
      current.loadingMore ||
      current.error ||
      current.page === 0 ||
      current.page >= current.pages
    )
      return;
    void request(current.page + 1, controller.signal);
  }, [enabled, load, request]);

  const retry = useCallback(() => {
    const current = stateRef.current;
    const controller = controllerRef.current;
    if (!enabled || !controller || !current.error) return;
    const page = current.page === 0 ? 1 : current.page + 1;
    void request(page, controller.signal);
  }, [enabled, request]);

  const current =
    state.load === load
      ? state
      : emptyState<T>(load, enabled);
  return {
    ...current,
    hasMore: current.page > 0 && current.page < current.pages,
    loadNext,
    retry,
  };
}
