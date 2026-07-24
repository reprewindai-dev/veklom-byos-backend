export interface VeklomClientOptions {
  apiKey?: string;
  accessToken?: string;
  baseUrl?: string;
}

export class PaymentRequiredError extends Error {
  public facilitatorUrl?: string;

  constructor(status: number, message: string, facilitatorUrl?: string) {
    super(`[X402 PAYWALL HIT] Free tier exhausted. To continue, authorize payment to: ${facilitatorUrl}\n\nDetails: HTTP ${status}: ${message}`);
    this.name = 'PaymentRequiredError';
    this.facilitatorUrl = facilitatorUrl;
  }
}

export interface CompletionRequest {
  prompt: string;
  model?: string;
  [key: string]: any;
}

export interface CompletionResponse {
  id: string;
  model: string;
  text: string;
  auditLogId: string | null;
  provider: string;
  tokensUsed: number;
  costUsd: number;
  contentSafetyScore: number;
  rawResponse: Record<string, any>;
}

export class VeklomClient {
  private baseUrl: string;
  private headers: Record<string, string>;

  constructor(options: VeklomClientOptions = {}) {
    this.baseUrl = (options.baseUrl || 'https://veklom.com/api/v1').replace(/\/+$/, '');
    this.headers = {
      'Content-Type': 'application/json',
    };

    if (options.accessToken) {
      this.headers['Authorization'] = `Bearer ${options.accessToken}`;
    } else if (options.apiKey) {
      this.headers['Authorization'] = `Bearer ${options.apiKey}`;
    }
  }

  private parseResponse(data: any): CompletionResponse {
    const choices = data.choices || [];
    const text = choices[0]?.message?.content || '';

    const usage = data.usage || {};
    const tokensUsed = usage.total_tokens || ((usage.prompt_tokens || 0) + (usage.completion_tokens || 0));

    const provider = data.id ? data.id.split('-')[0] : 'unknown';

    return {
      id: data.id || '',
      model: data.model || 'unknown',
      text,
      auditLogId: data.audit_log_id || null,
      provider,
      tokensUsed,
      costUsd: data.cost_usd || 0.0,
      contentSafetyScore: data.content_safety_score || 1.0,
      rawResponse: data,
    };
  }

  async complete(request: CompletionRequest): Promise<CompletionResponse> {
    const payload = {
      model: 'gpt-4o-mini', // default
      ...request,
    };

    const response = await fetch(`${this.baseUrl}/ai/complete`, {
      method: 'POST',
      headers: this.headers,
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const errorText = await response.text();
      if (response.status === 402) {
        throw new PaymentRequiredError(response.status, errorText, response.headers.get('x-402-facilitator-url') || undefined);
      }
      throw new Error(`Veklom API Error (${response.status}): ${errorText}`);
    }

    const data = await response.json();
    return this.parseResponse(data);
  }
}
