import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { cn } from "@/lib/utils";

type ToastTone = "default" | "success" | "warn" | "destructive";
type ToastItem = { id: number; title: string; description?: string; tone: ToastTone };

type ToastCtx = { push: (t: Omit<ToastItem, "id">) => void };

const Ctx = createContext<ToastCtx | null>(null);
let counter = 0;

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);
  const push = useCallback((t: Omit<ToastItem, "id">) => {
    const id = ++counter;
    setItems((prev) => [...prev, { ...t, id }]);
    setTimeout(() => setItems((prev) => prev.filter((x) => x.id !== id)), 4500);
  }, []);
  const value = useMemo(() => ({ push }), [push]);
  return (
    <Ctx.Provider value={value}>
      {children}
      <div className="pointer-events-none fixed bottom-4 right-4 z-[100] flex flex-col gap-2">
        {items.map((t) => (
          <div
            key={t.id}
            role="status"
            className={cn(
              "pointer-events-auto w-80 rounded-md border bg-card/95 p-3 shadow-lg animate-fade-up",
              t.tone === "destructive" && "border-destructive/40",
              t.tone === "success" && "border-success/40",
              t.tone === "warn" && "border-warn/40",
            )}
          >
            <div className="text-[12.5px] font-medium text-foreground">{t.title}</div>
            {t.description && (
              <div className="mt-0.5 text-[11.5px] leading-snug text-muted-foreground">{t.description}</div>
            )}
          </div>
        ))}
      </div>
    </Ctx.Provider>
  );
}

export function useToast() {
  const ctx = useContext(Ctx);
  if (!ctx) {
    return {
      toast: (t: Omit<ToastItem, "id"> | { title: string; description?: string; variant?: string }) => {
        // Fallback for when ToastProvider isn't mounted (e.g. early bootstrap).
        // eslint-disable-next-line no-console
        console.warn("[toast]", t);
      },
    };
  }
  return {
    toast: (t: { title: string; description?: string; variant?: "default" | "destructive" | "success" | "warn" }) =>
      ctx.push({ title: t.title, description: t.description, tone: t.variant ?? "default" }),
  };
}

export function _noop() {
  useEffect(() => undefined, []);
}
