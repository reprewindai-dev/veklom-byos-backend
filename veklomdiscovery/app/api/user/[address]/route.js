const ADDRESS_RE = /^0x[a-fA-F0-9]{40}$/;

export const revalidate = 60;

export async function GET(_request, { params }) {
  const { address } = await params;

  if (!ADDRESS_RE.test(address)) {
    return Response.json({ error: "Invalid EVM address" }, { status: 422 });
  }

  return Response.json({
    address,
    trustScore: 500,
    level: 1,
    completedMissions: 0,
    totalEarned: 0,
    agent: {
      id: `agent_${address.slice(0, 10)}`,
      owner: address,
      name: "Genesis",
      level: 1,
      policy: "balanced",
      trustScore: 500,
      wins: 0,
      losses: 0,
      totalEarned: 0,
    },
  }, {
    headers: {
      "Cache-Control": "public, s-maxage=60, stale-while-revalidate=300",
    },
  });
}
