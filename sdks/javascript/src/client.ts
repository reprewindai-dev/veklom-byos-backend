export interface VeklomClientOptions {
  apiKey: string;
  baseUrl?: string;
}

export interface CompleteRequest {
  model?: string;
  messages?: Array<{ role: string; content: string }>;
  prompt?: string;
  temperature?: number;
  [key: string]: any;
}

export interface CompleteResponse {
  text: string;
  auditLogId: string;
  provider: string;
  model: string;
  latencyMs: number;
  costUsd: number;
}

export class VeklomClient {
  private apiKey: string;
  private baseUrl: string;

  constructor(options: VeklomClientOptions) {
    this.apiKey = options.apiKey;
    this.baseUrl = (options.baseUrl || 'https://api.veklom.com/api/v1').replace(/\/$/, '');
  }

  async complete(request: CompleteRequest): Promise<CompleteResponse> {
    const { prompt, messages, ...rest } = request;
    
    if (!prompt && !messages) {
      throw new Error("Either 'messages' or 'prompt' must be provided.");
    }

    const payload = {
      model: 'llama3.2:latest',
      temperature: 0.7,
      messages: messages || (prompt ? [{ role: 'user', content: prompt }] : undefined),
      ...rest
    };

    const response = await fetch(`${this.baseUrl}/ai/complete`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${this.apiKey}`,
        'Content-Type': 'application/json',
        'User-Agent': 'veklom-javascript-sdk/0.1.0'
      },
      body: JSON.stringify(payload)
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Veklom API Error [${response.status}]: ${errorText}`);
    }

    const data = await response.json();

    return {
      text: data.response_text || '',
      auditLogId: String(data.audit_id || ''),
      provider: data.provider || 'unknown',
      model: data.model || 'unknown',
      latencyMs: data.latency_ms || 0,
      costUsd: data.cost_usd || 0.0
    };
  }
}
