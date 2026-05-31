/**
 * Billing, wallet, subscriptions, budgets, cost prediction.
 * Sources: backend/apps/api/routers/{billing,payments}.py
 */
import { http } from "@/lib/http";

export type WalletBalance = {
  balance: number;
  total_topped_up?: number;
  total_used?: number;
  updated_at?: string;
};
export type WalletTxn = {
  id: string;
  type: string;
  amount: number;
  description?: string;
  created_at: string;
};
export type Subscription = {
  id?: string;
  tier: string;
  status: string;
  current_period_end?: string;
  seats?: number;
};
export type SubscriptionPlan = {
  id: string;
  name: string;
  price_usd: number;
  period?: "monthly" | "annual" | string;
  features?: string[];
};
export type BudgetRule = {
  id: string;
  type: "daily" | "weekly" | "monthly" | string;
  amount: number;
  alert_thresholds?: number[];
};

export const billingApi = {
  wallet: {
    balance: () => http.get<WalletBalance>("/wallet/balance"),
    transactions: (q: { limit?: number; offset?: number } = {}) =>
      http.get<{ items: WalletTxn[]; total: number }>("/wallet/transactions", { query: q }),
    topupOptions: () => http.get<{ options: { id: string; tier: string; amount: number; price: number }[] }>(
      "/wallet/topup/options",
    ),
    topupCheckout: (body: { tier: string; success_url: string; cancel_url: string }) =>
      http.post<{ checkout_url: string; session_id: string }>("/wallet/topup/checkout", body),
  },
  subscriptions: {
    current: () => http.get<Subscription>("/subscriptions/current"),
    plans: () => http.get<{ plans: SubscriptionPlan[] }>("/subscriptions/plans"),
    checkout: (body: { plan_id: string; success_url: string; cancel_url: string }) =>
      http.post<{ checkout_url: string; session_id: string }>("/subscriptions/checkout", body),
  },
  invoices: () => http.get<{ items: { id: string; period: string; total_usd: number; pdf_url?: string }[] }>(
    "/billing/invoices",
  ),
  budget: {
    list: () => http.get<{ rules: BudgetRule[] }>("/budget/rules"),
    create: (body: Omit<BudgetRule, "id">) => http.post<BudgetRule>("/budget/rules", body),
    remove: (id: string) => http.delete<void>(`/budget/rules/${encodeURIComponent(id)}`),
  },
  cost: {
    predict: () => http.get<{ predicted_monthly_usd: number }>("/cost/predict"),
  },
};
