/**
 * AI execution — /api/v1/ai/* and /api/v1/v1/exec
 * Source: backend/apps/api/routers/ai.py + exec_router.py
 */
import { http } from "@/lib/http";
import type { AICompleteRequest, AICompleteResponse } from "./types";

export type AIModelEntry = {
  id: string;
  name: string;
  provider: string;
  context?: number;
  modality?: string;
  enabled?: boolean;
  bedrock_model_id?: string;
  pricing?: { input?: number; output?: number };
};

export type PredictCostRequest = { model: string; prompt: string; expected_output_tokens?: number };
export type PredictCostResponse = {
  predicted_tokens: number;
  predicted_cost_usd: number;
  model: string;
};

export const aiApi = {
  models: () => http.get<{ models: AIModelEntry[] }>("/ai/models"),
  complete: (body: AICompleteRequest) => http.post<AICompleteResponse>("/ai/complete", body),
  predictCost: (body: PredictCostRequest) => http.post<PredictCostResponse>("/ai/predict-cost", body),
  /** SSE streaming inference. Caller wires EventSource directly because Authorization
   *  cannot be set on EventSource — backend supports `?access_token=` as a fallback. */
  execStreamUrl: (params: { access_token: string }) =>
    http.url("/api/v1/v1/exec", { access_token: params.access_token }),
  upload(file: File) {
    const fd = new FormData();
    fd.append("file", file);
    // Reach through fetch directly because http expects JSON.
    return fetch(http.url("/upload"), {
      method: "POST",
      body: fd,
      headers: { Authorization: `Bearer ${localStorage.getItem("veklom_token") ?? ""}` },
      credentials: "include",
    }).then((r) => {
      if (!r.ok) throw new Error(`Upload failed: ${r.status}`);
      return r.json() as Promise<{ file_id: string; url?: string }>;
    });
  },
};
