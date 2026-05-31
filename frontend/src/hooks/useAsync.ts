import { useCallback, useEffect, useRef, useState } from 'react';
import { ApiError } from '../lib/http';

export interface AsyncState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  status: number | null;
  refetch: () => void;
}

// Runs an async fetcher on mount (and when deps change). Surfaces the real
// error message/status — never substitutes fake data on failure.
export function useAsync<T>(fetcher: () => Promise<T>, deps: unknown[] = []): AsyncState<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<number | null>(null);
  const mounted = useRef(true);
  const tick = useRef(0);

  const run = useCallback(() => {
    const current = ++tick.current;
    setLoading(true);
    setError(null);
    fetcher()
      .then((res) => {
        if (mounted.current && current === tick.current) {
          setData(res);
          setStatus(200);
        }
      })
      .catch((err: unknown) => {
        if (mounted.current && current === tick.current) {
          setError(err instanceof Error ? err.message : String(err));
          setStatus(err instanceof ApiError ? err.status : null);
        }
      })
      .finally(() => {
        if (mounted.current && current === tick.current) setLoading(false);
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  useEffect(() => {
    mounted.current = true;
    run();
    return () => {
      mounted.current = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  return { data, loading, error, status, refetch: run };
}
