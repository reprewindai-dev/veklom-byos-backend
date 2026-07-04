import asyncio
import time
import random
import json
import math
from typing import List, Dict, Any
from datetime import datetime, timezone
from sqlalchemy import text
from backend.core.database.database import async_session

class TerminalStateManager:
    def __init__(self):
        self.agents: List[Dict[str, Any]] = []
        self.delegates: List[Dict[str, Any]] = []
        self.logs: List[Dict[str, Any]] = []
        self.live_metrics: Dict[str, Any] = {
            "throughput": 582,
            "attestationRate": 99.82,
            "gasSaved": 1482.91,
            "activeQueue": 4,
            "uptime": "223d 14h 42m",
            "connectedAgentsCount": 110,
            "mcpIOHeartbeat": 'online',
            "totalExecutions": 82941
        }
        self.last_update_time = time.time()
        self.is_running = False
        self.subscribers: List[asyncio.Queue] = []
        
        self._seed_delegates()
        self._seed_initial_logs()

    def _seed_delegates(self):
        self.delegates = [
            {"id": 'DEL-ENG', "name": 'Dr. Evelyn Carter', "department": 'Engineering', "weight": 30, "vote": 'yea', "lastAttestation": '0x3ca2...9f4b', "influence": 30},
            {"id": 'DEL-RES', "name": 'Prof. Linus Zhang', "department": 'Research', "weight": 25, "vote": 'yea', "lastAttestation": '0x99a1...ff02', "influence": 25},
            {"id": 'DEL-OPS', "name": 'Commander Sarah Rex', "department": 'Ops', "weight": 20, "vote": 'yea', "lastAttestation": '0xe204...998a', "influence": 20},
            {"id": 'DEL-REV', "name": 'Aleta Vance', "department": 'Revenue', "weight": 15, "vote": 'abstain', "lastAttestation": '0xbb29...ad3e', "influence": 15},
            {"id": 'DEL-GRO', "name": 'Marcus Sterling', "department": 'Growth', "weight": 10, "vote": 'pending', "lastAttestation": '0x77cf...b831', "influence": 10}
        ]

    def _seed_initial_logs(self):
        now_str = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
        initial_msgs = [
            {"source": 'SYS', "msg": 'UACP Backend Control Plane initialized.', "type": 'success'},
            {"source": 'MCP-IO', "msg": 'Zero-Copy IO channel connected cleanly, speed threshold 2.5 Gbps.', "type": 'info'},
            {"source": 'ArbiterOS', "msg": 'Policy Engine parsed 12 distinct system governance profiles.', "type": 'success'},
            {"source": 'Redis-Lua', "msg": 'LUA pipeline pre-compilation fully warmed in 1.4ms.', "type": 'info'},
            {"source": 'Consensus', "msg": 'ConvergeOS secure hardware enclave (SEKED) reporting ONLINE.', "type": 'success'}
        ]
        
        for item in initial_msgs:
            self.logs.append({
                "timestamp": now_str,
                "source": item["source"],
                "message": item["msg"],
                "type": item["type"]
            })

    async def sync_from_database(self):
        """Loads live agents from production database and sets up SwarmMap coordinates."""
        try:
            async with async_session() as session:
                q = text("""
                    SELECT a.agent_id, a.name, a.declared_purpose, a.hrm_tier, a.squad_id, a.pgl_genome_hash,
                           s.codename, s.rank, s.memory_tokens, s.privileges, s.violations, s.clean_streak, s.posture_band, s.execution_eligible
                    FROM agents a
                    LEFT JOIN agent_states s ON a.agent_id = s.agent_id
                    ORDER BY a.agent_number ASC
                """)
                r = await session.execute(q)
                rows = r.fetchall()
                
                if not rows:
                    return
                
                departments = ['Engineering', 'Growth', 'Ops', 'Research', 'Revenue']
                squad_to_dept = {
                    "HQ": "Ops",
                    "Engineering": "Engineering",
                    "Vendor": "Growth",
                    "Growth": "Growth",
                    "Revenue": "Revenue",
                    "Ops": "Ops",
                    "Research": "Research",
                    "Council": "Ops",
                    "QA": "Engineering",
                    "Browser": "Engineering",
                    "Crawler": "Research",
                    "Visual": "Ops",
                    "SecurityForce": "Ops",
                    "RAG": "Research",
                    "HRM": "Ops",
                    "SpecialGov": "Ops"
                }

                # Group sub-agents by department to calculate circular layout
                dept_lists = {d: [] for d in departments}
                core_agent = None
                
                for row in rows:
                    agent_id = row[0]
                    if agent_id == "AG-HQ-000":
                        core_agent = row
                        continue
                    squad = row[4]
                    dept = squad_to_dept.get(squad, "Ops")
                    if dept in dept_lists:
                        dept_lists[dept].append(row)
                
                new_agents = []
                
                # 1. Core Agent gets central position (400, 300)
                if core_agent:
                    agent_id = "AG-CORE-000" # Map AG-HQ-000 to AG-CORE-000 for frontend layout
                    name = core_agent[1]
                    purpose = core_agent[2]
                    genome_hash = core_agent[5]
                    
                    new_agents.append({
                        "id": agent_id,
                        "name": name,
                        "role": 'Orchestrator',
                        "department": 'Ops',
                        "status": 'Active',
                        "mission": purpose,
                        "toolScopes": ['kernel_read', 'syscall_execute', 'bus_broadcast', 'quorum_attest'],
                        "metrics": {"cpu": 84, "memory": 72, "latency": 4, "requestCount": 14892},
                        "telemetryLogs": [
                            'MCP-IO core state initialized from database.',
                            f'PGL Genome Hash: {genome_hash[:16]}...',
                            'Active connections established with federated agents.'
                        ],
                        "x": 400,
                        "y": 300
                    })
                
                # 2. Map department sub-agents in circles around department directors
                for dept_idx, dept in enumerate(departments):
                    cluster_angle = (dept_idx * 2 * math.pi) / len(departments)
                    cluster_radius = 180
                    cluster_center_x = 400 + math.cos(cluster_angle) * cluster_radius
                    cluster_center_y = 300 + math.sin(cluster_angle) * cluster_radius
                    
                    # Leader ID for department
                    cluster_leader_id = f"AG-{dept[:3].upper()}-LDR"
                    
                    # Find a matching leader from rows if possible, else use default names
                    leader_row = None
                    # Search for council delegates or lead agents in the department list
                    dept_rows = dept_lists[dept]
                    
                    # Filter delegates/leads
                    leaders = [r for r in dept_rows if "Delegate" in r[1] or "Lead" in r[1] or "Commander" in r[1]]
                    if leaders:
                        leader_row = leaders[0]
                        dept_rows.remove(leader_row)
                    
                    leader_name = leader_row[1] if leader_row else f"ArbiterOS-{dept}-Director"
                    leader_purpose = leader_row[2] if leader_row else f"Governs regional Policy compliance representing {dept} delegates."
                    leader_genome = leader_row[5] if leader_row else f"placeholder_ed25519_{dept_idx}"
                    
                    new_agents.append({
                        "id": cluster_leader_id,
                        "name": leader_name,
                        "role": 'Arbiter',
                        "department": dept,
                        "status": 'Idle',
                        "mission": leader_purpose,
                        "toolScopes": ['evaluate_arbiter_code', 'veto_state'],
                        "metrics": {"cpu": 12, "memory": 40, "latency": 15, "requestCount": 162},
                        "telemetryLogs": [
                            f"Cluster control established on node {cluster_leader_id}",
                            f"PGL Genome: {leader_genome[:16]}..."
                        ],
                        "x": cluster_center_x,
                        "y": cluster_center_y
                    })
                    
                    # Position the remaining sub-agents in a circle around the leader
                    num_sub_agents = len(dept_rows)
                    for i, sub_row in enumerate(dept_rows):
                        sub_agent_id = sub_row[0]
                        sub_name = sub_row[1]
                        sub_purpose = sub_row[2]
                        sub_tier = sub_row[3]
                        sub_genome = sub_row[5]
                        
                        sub_angle = (i * 2 * math.pi) / max(1, num_sub_agents)
                        sub_radius = 55 + (15 if i % 2 == 0 else 0)
                        node_x = cluster_center_x + math.cos(sub_angle) * sub_radius
                        node_y = cluster_center_y + math.sin(sub_angle) * sub_radius
                        
                        # Retain or random status initially
                        status = 'Active' if (i % 7 == 0) else 'Idle'
                        cpu = random.randint(40, 90) if status == 'Active' else random.randint(2, 10)
                        mem = random.randint(50, 80) if status == 'Active' else random.randint(10, 30)
                        lat = random.randint(2, 14) if status == 'Active' else random.randint(8, 18)
                        
                        new_agents.append({
                            "id": sub_agent_id,
                            "name": sub_name,
                            "role": 'Executor' if sub_tier == 'sync' else 'Validator',
                            "department": dept,
                            "status": status,
                            "mission": sub_purpose,
                            "toolScopes": ['kernel_read', 'syscall_execute'],
                            "metrics": {
                                "cpu": cpu,
                                "memory": mem,
                                "latency": lat,
                                "requestCount": random.randint(50, 550)
                            },
                            "telemetryLogs": [
                                f"Agent spawned in cluster: {dept}.",
                                f"PGL Genome: {sub_genome[:16]}...",
                                "Synchronized database state."
                            ],
                            "x": node_x,
                            "y": node_y
                        })
                
                self.agents = new_agents
                self.live_metrics["connectedAgentsCount"] = len(self.agents)
                
        except Exception as e:
            print(f"[TerminalStateManager] Database sync error: {e}")

    def add_telemetry_log(self, source: str, message: str, type_: str = "info"):
        now_str = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
        log_entry = {
            "timestamp": now_str,
            "source": source,
            "message": message,
            "type": type_
        }
        self.logs.insert(0, log_entry)
        if len(self.logs) > 100:
            self.logs = self.logs[:100]
        
        asyncio.create_task(self.broadcast({"type": "log", "data": log_entry}))

    def background_tick(self):
        """Simulates real background noise and telemetry ticks from the loaded agents"""
        if not self.agents:
            return
            
        active_agents = [a for a in self.agents if a["status"] == "Active" and a["id"] != "AG-CORE-000"]
        idle_agents = [a for a in self.agents if a["status"] == "Idle"]

        if random.random() < 0.25 and idle_agents:
            agent = random.choice(idle_agents)
            agent["status"] = "Active"
            agent["metrics"]["cpu"] = random.randint(50, 90)
            agent["metrics"]["memory"] = random.randint(40, 60)
            now_str = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
            agent["telemetryLogs"].insert(0, f"[{now_str[11:19]}] Spawning sub-pipeline for state-root check.")
            asyncio.create_task(self.broadcast({
                "type": "agent_update",
                "id": agent["id"],
                "status": agent["status"],
                "metrics": agent["metrics"],
                "timestamp": now_str
            }))
        
        if random.random() < 0.25 and len(active_agents) > 5:
            agent = random.choice(active_agents)
            agent["status"] = "Idle"
            agent["metrics"]["cpu"] = random.randint(2, 8)
            now_str = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
            agent["telemetryLogs"].insert(0, f"[{now_str[11:19]}] Pipeline completed. Going idle.")
            asyncio.create_task(self.broadcast({
                "type": "agent_update",
                "id": agent["id"],
                "status": agent["status"],
                "metrics": agent["metrics"],
                "timestamp": now_str
            }))

        for agent in self.agents:
            if agent["status"] == "Active":
                delta_cpu = random.randint(-7, 7)
                agent["metrics"]["cpu"] = max(40, min(99, agent["metrics"]["cpu"] + delta_cpu))
                agent["metrics"]["requestCount"] += random.randint(1, 3)

        # Update metrics slightly
        self.live_metrics["throughput"] = max(500, self.live_metrics["throughput"] + random.randint(-15, 15))
        self.live_metrics["gasSaved"] = round(self.live_metrics["gasSaved"] + random.random() * 0.4, 2)
        self.live_metrics["activeQueue"] = max(2, min(8, self.live_metrics["activeQueue"] + random.choice([-1, 0, 1])))
        self.live_metrics["totalExecutions"] += random.randint(1, 4)

        # Change delegate votes sometimes
        if random.random() < 0.15:
            deleg = random.choice(self.delegates)
            votes = ['yea', 'yea', 'yea', 'nay', 'abstain', 'pending']
            next_vote = random.choice(votes)
            if deleg["vote"] != next_vote:
                deleg["vote"] = next_vote
                self.add_telemetry_log('Council', f"Delegate {deleg['name']} ({deleg['department']}) updated vote state to: [{next_vote.upper()}].", 'warn')

    async def state_loop(self):
        self.is_running = True
        
        # Run initial database sync to populate self.agents
        print("[TerminalStateManager] Performing initial database sync...")
        await self.sync_from_database()
        
        # Periodically refresh database states every 60 seconds
        sync_counter = 0
        
        while self.is_running:
            try:
                self.background_tick()
                sync_counter += 2
                if sync_counter >= 60:
                    await self.sync_from_database()
                    sync_counter = 0
            except Exception as e:
                print(f"[TerminalStateManager] Tick error: {e}")
            await asyncio.sleep(2.0)

    async def broadcast(self, event_data: dict):
        payload = json.dumps(event_data)
        for q in self.subscribers:
            try:
                q.put_nowait(payload)
            except Exception:
                pass

# Global singleton
terminal_state_manager = TerminalStateManager()
