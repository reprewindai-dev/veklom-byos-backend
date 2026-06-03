"use client";

import clsx from "clsx";
import { ReactNode } from "react";

export function PageHeader({ title, subtitle, actions }: { title: string; subtitle?: string; actions?: ReactNode }) {
  return (
    <div className="flex items-start gap-4 mb-6">
      <div>
        <h1 className="text-xl font-semibold tracking-tight">{title}</h1>
        {subtitle && <p className="text-sm text-ink-400 mt-1 max-w-2xl">{subtitle}</p>}
      </div>
      {actions && <div className="ml-auto flex items-center gap-2">{actions}</div>}
    </div>
  );
}

export function Card({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={clsx("card p-5", className)}>{children}</div>;
}

export function StatCard({ label, value, hint, accent }: { label: string; value: ReactNode; hint?: string; accent?: string }) {
  return (
    <Card className="min-w-0">
      <div className="text-[11px] uppercase tracking-widest text-ink-400">{label}</div>
      <div className={clsx("mt-1 text-2xl font-semibold", accent)}>{value}</div>
      {hint && <div className="text-xs text-ink-400 mt-1">{hint}</div>}
    </Card>
  );
}

export function Empty({ title, hint }: { title: string; hint?: string }) {
  return (
    <Card className="text-center py-10">
      <div className="text-ink-200">{title}</div>
      {hint && <div className="text-xs text-ink-400 mt-1">{hint}</div>}
    </Card>
  );
}

export function ErrorBox({ message }: { message: string }) {
  return (
    <div className="card p-4 border-accent-red/40 text-accent-red text-sm">
      {message}
    </div>
  );
}

export function Skeleton({ className }: { className?: string }) {
  return <div className={clsx("animate-pulse bg-bg-700 rounded-md", className)} />;
}

export function Table<T>({
  rows, columns, empty, rowKey,
}: {
  rows: T[];
  columns: { key: string; header: string; render: (r: T) => ReactNode; width?: string }[];
  empty?: string;
  rowKey: (r: T) => string;
}) {
  if (!rows || rows.length === 0) return <Empty title={empty || "No records"} />;
  return (
    <Card className="overflow-x-auto p-0">
      <table className="min-w-full text-sm">
        <thead>
          <tr className="text-left text-[11px] uppercase tracking-widest text-ink-400 border-b border-border">
            {columns.map((c) => (
              <th key={c.key} className="px-4 py-3 font-medium" style={{ width: c.width }}>{c.header}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={rowKey(r)} className="border-b border-border/60 last:border-0 hover:bg-bg-700/40">
              {columns.map((c) => (
                <td key={c.key} className="px-4 py-3 align-top">{c.render(r)}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </Card>
  );
}

export function Button({ children, onClick, variant = "primary", type = "button", disabled, className }: {
  children: ReactNode; onClick?: () => void; variant?: "primary" | "ghost" | "danger"; type?: "button" | "submit"; disabled?: boolean; className?: string;
}) {
  return (
    <button
      type={type} onClick={onClick} disabled={disabled}
      className={clsx(
        "inline-flex items-center px-3 py-1.5 rounded-md text-sm font-medium transition disabled:opacity-50",
        variant === "primary" && "bg-brand-500 hover:bg-brand-600 text-bg-900",
        variant === "ghost" && "bg-bg-700 hover:bg-bg-600 text-ink-50",
        variant === "danger" && "bg-accent-red/20 hover:bg-accent-red/30 text-accent-red border border-accent-red/40",
        className
      )}
    >
      {children}
    </button>
  );
}
