import { getNotificationUsers } from "../../../../server/baseNotifications";

export const dynamic = "force-dynamic";

export async function GET(request) {
  return getNotificationUsers(request);
}
