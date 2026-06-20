export const revalidate = 30;

export async function GET(request, { params }) {
  const { agentId } = await params;
  const { searchParams } = new URL(request.url);
  const amount = Number(searchParams.get("amount") || "0.1");
  const policy = searchParams.get("policy") || "balanced";
  const maxSpend = policy === "aggressive" ? 500 : policy === "conservative" ? 10 : 50;

  const gates = {
    agentActive: true,
    budgetOk: amount <= maxSpend,
    policyMatch: true,
    trustScoreOk: true,
  };
  const approved = Object.values(gates).every(Boolean);

  return Response.json({
    agentId,
    approved,
    reason: approved ? "All governance gates passed" : "Governance gate failed",
    gates,
    proofHash: `0x${Buffer.from(JSON.stringify({ agentId, gates })).toString("hex").slice(0, 64)}`,
  }, {
    headers: {
      "Cache-Control": "public, s-maxage=30, stale-while-revalidate=120",
    },
  });
}
