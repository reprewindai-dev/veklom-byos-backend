import { getNotificationStatus } from "../../../../server/baseNotifications";

export const dynamic = "force-dynamic";

export async function POST(request) {
  return getNotificationStatus(request);
}
