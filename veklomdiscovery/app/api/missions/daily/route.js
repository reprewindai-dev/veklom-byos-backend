export const revalidate = 300;

export async function GET() {
  return Response.json({
    missions: [
      {
        id: "mission_1",
        title: "First Claim",
        description: "Claim your daily USDC drop",
        reward: { usdc: 0.5, xp: 100 },
        type: "first_claim",
        completed: false,
        expiresAt: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString(),
      },
      {
        id: "mission_2",
        title: "Trade Pulse",
        description: "Complete any onchain action",
        reward: { usdc: 0.75, xp: 150 },
        type: "trade_pulse",
        completed: false,
        expiresAt: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString(),
      },
      {
        id: "mission_3",
        title: "Arena Brave",
        description: "Launch one governed race",
        reward: { usdc: 0.5, xp: 125 },
        type: "arena_brave",
        completed: false,
        expiresAt: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString(),
      },
    ],
  }, {
    headers: {
      "Cache-Control": "public, s-maxage=300, stale-while-revalidate=900",
    },
  });
}
