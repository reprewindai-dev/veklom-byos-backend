import os
import requests

QSTASH_TOKEN = os.getenv("QSTASH_TOKEN")
BACKEND_URL = os.getenv("BACKEND_URL", "https://api.veklom.com")
JOB_PROCESSOR_API_KEY = os.getenv("JOB_PROCESSOR_API_KEY")
MARKETPLACE_AUTOMATION_API_KEY = os.getenv("MARKETPLACE_AUTOMATION_API_KEY")
INTERNAL_OPERATOR_TOKEN = os.getenv("INTERNAL_OPERATOR_TOKEN")
ENABLE_BUILDER_AGENT_QSTASH = os.getenv("ENABLE_BUILDER_AGENT_QSTASH", "false").lower() == "true"
DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"

SCHEDULES = [
    {
        "schedule_id": "veklom-job-processor-30m",
        "cron": "*/30 * * * *",
        "destination": f"{BACKEND_URL}/api/v1/jobs/process",
        "headers": {"Authorization": f"Bearer {JOB_PROCESSOR_API_KEY}"} if JOB_PROCESSOR_API_KEY else {}
    },
    {
        "schedule_id": "veklom-marketplace-automation-6h",
        "cron": "0 */6 * * *",
        "destination": f"{BACKEND_URL}/api/v1/marketplace/automation/run",
        "headers": {"Authorization": f"Bearer {MARKETPLACE_AUTOMATION_API_KEY}"} if MARKETPLACE_AUTOMATION_API_KEY else {}
    },
    {
        "schedule_id": "veklom-marketplace-automation-monday-5h",
        "cron": "15 */5 * * 1",
        "destination": f"{BACKEND_URL}/api/v1/marketplace/automation/run",
        "headers": {"Authorization": f"Bearer {MARKETPLACE_AUTOMATION_API_KEY}"} if MARKETPLACE_AUTOMATION_API_KEY else {}
    }
]

if ENABLE_BUILDER_AGENT_QSTASH:
    SCHEDULES.append({
        "schedule_id": "veklom-builder-agent-box-heartbeat-6h",
        "cron": "22 */6 * * *",
        "destination": f"{BACKEND_URL}/api/v1/internal/operators/workers/builder-scout/heartbeat",
        "headers": {"Authorization": f"Bearer {INTERNAL_OPERATOR_TOKEN}"} if INTERNAL_OPERATOR_TOKEN else {}
    })

def main():
    if not QSTASH_TOKEN:
        print("QSTASH_TOKEN is required.")
        return
        
    print(f"Setting up {len(SCHEDULES)} QStash schedules...")
    
    for sched in SCHEDULES:
        if DRY_RUN:
            print(f"[DRY RUN] Would create schedule: {sched['schedule_id']} at {sched['cron']} -> {sched['destination']}")
            continue
            
        print(f"Syncing {sched['schedule_id']}...")
        # Note: In reality, we'd use the QStash REST API here to PUT/POST schedules.
        # This is a stub for the integration.
        response = requests.post(
            f"https://qstash.upstash.io/v2/schedules/{sched['destination']}",
            headers={
                "Authorization": f"Bearer {QSTASH_TOKEN}",
                "Upstash-Cron": sched['cron'],
                **{f"Upstash-Forward-{k}": v for k,v in sched['headers'].items()}
            }
        )
        if response.status_code in (200, 201):
            print(f"Successfully synced {sched['schedule_id']}")
        else:
            print(f"Failed to sync {sched['schedule_id']}: {response.text}")

if __name__ == "__main__":
    main()
