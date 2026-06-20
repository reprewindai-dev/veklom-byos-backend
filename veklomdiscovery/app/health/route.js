export const revalidate = 60;

export async function GET() {
  return Response.json({
    status: "ok",
    veklomAddress: process.env.NEXT_PUBLIC_VEKLOM_ADDRESS || process.env.VEKLOM_ADDRESS || "0xCC34553b4e6332ffb9C1b61E22436ACA53113D1d",
    veklomComAddress: process.env.NEXT_PUBLIC_VEKLOM_COM_ADDRESS || process.env.VEKLOM_COM_ADDRESS || process.env.NEXT_PUBLIC_VEKLOM_ADDRESS || process.env.VEKLOM_ADDRESS || "0xCC34553b4e6332ffb9C1b61E22436ACA53113D1d",
    veklomIdAddress: process.env.NEXT_PUBLIC_VEKLOM_ID_ADDRESS || "0x3a74772e925b54F7dAD7FD95c9Ba30825033f970",
    baseAppId: process.env.NEXT_PUBLIC_BASE_APP_ID || "6a20f24cc341f72c2f573eb5",
    veklomENS: "veklom.base.eth",
    service: "veklomdiscovery",
    timestamp: new Date().toISOString(),
  }, {
    headers: {
      "Cache-Control": "public, s-maxage=60, stale-while-revalidate=300",
    },
  });
}
