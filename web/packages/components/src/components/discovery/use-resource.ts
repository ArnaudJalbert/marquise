import { useEffect, useState } from "react";

type Resource<T> = { data?: T; error?: Error; loading: boolean };

/** The memoized loader is the request identity, including the injected client. */
export function useResource<T>(
  load: (signal: AbortSignal) => Promise<T>,
): Resource<T> & { retry: () => void } {
  const [state, setState] = useState<Resource<T> & { load: typeof load }>({
    load,
    loading: true,
  });
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setState({ load, loading: true });
    load(controller.signal).then(
      (data) => {
        if (!controller.signal.aborted)
          setState({ load, data, loading: false });
      },
      (error: unknown) => {
        if (!controller.signal.aborted)
          setState({
            load,
            error: error instanceof Error ? error : new Error(String(error)),
            loading: false,
          });
      },
    );
    return () => controller.abort();
  }, [load, retry]);
  // Do not show a previous query's results while the next effect starts.
  const current = state.load === load ? state : { loading: true };
  return { ...current, retry: () => setRetry((value) => value + 1) };
}
