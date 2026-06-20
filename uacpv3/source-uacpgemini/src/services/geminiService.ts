import { GoogleGenAI, Type } from "@google/genai";

let ai: GoogleGenAI | null = null;

function getAI() {
  if (!ai) {
    const apiKey = process.env.GEMINI_API_KEY;
    if (!apiKey) {
      throw new Error("GEMINI_API_KEY environment variable is required");
    }
    ai = new GoogleGenAI({ apiKey });
  }
  return ai;
}

export async function decodeIntentToPlan(intent: string) {
  const model = "gemini-3-flash-preview";
  const genAI = getAI();
  
  const systemInstruction = `
    You are the Quantum UACP Intent Interpreter.
    Your job is to convert natural language user intent into a structured execution graph for hybrid quantum/classical workflows.
    
    Einstein once said "God does not play dice with the universe", expressing skepticism about the probabilistic nature of quantum mechanics.
    However, in UACP, we acknowledge the probabilistic bottom (quantum) but demand a deterministic top (orchestration).
    
    Generate a JSON response that follows this schema:
    {
      "name": "A concise name for the plan",
      "graph": {
        "nodes": [
          { "id": "node-1", "type": "quantum_gate" | "classical_compute" | "measurement", "description": "..." }
        ],
        "edges": [
          { "from": "node-1", "to": "node-2" }
        ]
      },
      "rationale": "How this plan addresses Einstein's concern by enforcing order over randomness."
    }
  `;

  try {
    const response = await genAI.models.generateContent({
      model,
      contents: intent,
      config: {
        systemInstruction,
        responseMimeType: "application/json",
        responseSchema: {
          type: Type.OBJECT,
          properties: {
            name: { type: Type.STRING },
            graph: {
              type: Type.OBJECT,
              properties: {
                nodes: {
                  type: Type.ARRAY,
                  items: {
                    type: Type.OBJECT,
                    properties: {
                      id: { type: Type.STRING },
                      type: { type: Type.STRING, enum: ["quantum_gate", "classical_compute", "measurement"] },
                      description: { type: Type.STRING }
                    },
                    required: ["id", "type", "description"]
                  }
                },
                edges: {
                  type: Type.ARRAY,
                  items: {
                    type: Type.OBJECT,
                    properties: {
                      from: { type: Type.STRING },
                      to: { type: Type.STRING }
                    }
                  }
                }
              }
            },
            rationale: { type: Type.STRING }
          },
          required: ["name", "graph", "rationale"]
        }
      }
    });

    const text = response.text || "{}";
    return JSON.parse(text);
  } catch (error) {
    console.error("Gemini Intent Decoding Error:", error);
    return {
      name: "Emergency Fallback Plan",
      graph: { nodes: [{ id: 'n1', type: 'classical_compute', description: 'Fallback recovery' }], edges: [] },
      rationale: "System was unable to parse complex intent. Einstein's order was compromised."
    };
  }
}
