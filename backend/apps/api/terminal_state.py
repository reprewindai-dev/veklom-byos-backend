import asyncio
import time
import random
from typing import List, Dict, Any
from datetime import datetime, timezone

# We use an in-memory store for speed, backed by realistic data structures
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
            "connectedAgentsCount": 120,
            "mcpIOHeartbeat": 'online',
            "totalExecutions": 82941
        }
        self.last_update_time = time.time()
        self.is_running = False
        self.subscribers: List[asyncio.Queue] = []
        
        self._seed_delegates()
        self._seed_system_agents()
        self._seed_initial_logs()

    def _seed_delegates(self):
        self.delegates = [
            {"id": 'DEL-ENG', "name": 'Dr. Evelyn Carter', "department": 'Engineering', "weight": 30, "vote": 'yea', "lastAttestation": '0x3ca2...9f4b', "influence": 30},
            {"id": 'DEL-RES', "name": 'Prof. Linus Zhang', "department": 'Research', "weight": 25, "vote": 'yea', "lastAttestation": '0x99a1...ff02', "influence": 25},
            {"id": 'DEL-OPS', "name": 'Commander Sarah Rex', "department": 'Ops', "weight": 20, "vote": 'yea', "lastAttestation": '0xe204...998a', "influence": 20},
            {"id": 'DEL-REV', "name": 'Aleta Vance', "department": 'Revenue', "weight": 15, "vote": 'abstain', "lastAttestation": '0xbb29...ad3e', "influence": 15},
            {"id": 'DEL-GRO', "name": 'Marcus Sterling', "department": 'Growth', "weight": 10, "vote": 'pending', "lastAttestation": '0x77cf...b831', "influence": 10}
        ]

    def _seed_system_agents(self):
        departments = ['Engineering', 'Growth', 'Ops', 'Research', 'Revenue']
        roles = ['Executor', 'Validator', 'Executor', 'Validator', 'Router']
        
        # Root Agent
        self.agents.append({
            "id": 'AG-CORE-000',
            "name": 'MCP-IO-BUS-CORE',
            "role": 'Orchestrator',
            "department": 'Ops',
            "status": 'Active',
            "mission": 'High-throughput execution multiplexer and PGL consensus sequencer.',
            "toolScopes": ['kernel_read', 'syscall_execute', 'bus_broadcast', 'quorum_attest'],
            "metrics": {"cpu": 84, "memory": 72, "latency": 4, "requestCount": 14892},
            "telemetryLogs": [
                'MCP-IO core state initialized.',
                'Awaiting consensus attestation loop.',
                'Active connections established with 105 federated sub-agents.'
            ],
            "x": 400,
            "y": 300
        })

        import math
        id_counter = 1
        
        missions_by_dept = {
            'Engineering': ['Kernel compiler and automated build validation', 'ZKP verification processor', 'Virtual VM observer'],
            'Growth': ['Expansion metric tracker', 'Dynamic indexing coordinator', 'Cross-chain load balancer'],
            'Ops': ['Redis cluster health analyzer', 'Docker sandbox container restarter', 'Network delay telemetry'],
            'Research': ['Deep pattern mining', 'ArbiterOS policy rule validator', 'Zero-knowledge prover optimization'],
            'Revenue': ['Gas fee scheduler', 'Multi-currency hedge arbiter', 'Throughput-to-gas ratio optimizer']
        }

        tools_by_dept = {
            'Engineering': ['run_bundler', 'verify_zkp', 'git_diff', 'clean_vm_state'],
            'Growth': ['query_telemetry', 'adjust_rates', 'broadcast_state', 'trigger_load_shed'],
            'Ops': ['tcp_probe', 'flush_redis', 'reboot_sandbox', 'measure_latency'],
            'Research': ['parse_policy', 'compile_rules', 'prove_state', 'estimate_entropy'],
            'Revenue': ['calculate_gas', 'route_hedge', 'payout_attest', 'optimize_gas_limit']
        }

        for dept_idx, dept in enumerate(departments):
            cluster_angle = (dept_idx * 2 * math.pi) / len(departments)
            cluster_radius = 180
            cluster_center_x = 400 + math.cos(cluster_angle) * cluster_radius
            cluster_center_y = 300 + math.sin(cluster_angle) * cluster_radius

            cluster_leader_id = f"AG-{dept[:3].upper()}-LDR"
            self.agents.append({
                "id": cluster_leader_id,
                "name": f"ArbiterOS-{dept}-Director",
                "role": 'Arbiter',
                "department": dept,
                "status": 'Idle',
                "mission": f"Governs regional Policy compliance representing {dept} delegates.",
                "toolScopes": tools_by_dept[dept] + ['evaluate_arbiter_code', 'veto_state'],
                "metrics": {"cpu": 12, "memory": 40, "latency": 15, "requestCount": 162},
                "telemetryLogs": [f"Cluster control established on node {cluster_leader_id}"],
                "x": cluster_center_x,
                "y": cluster_center_y
            })

            num_sub_agents = 23
            for i in range(num_sub_agents):
                sub_angle = (i * 2 * math.pi) / num_sub_agents
                sub_radius = 55 + (15 if i % 2 == 0 else 0)
                node_x = cluster_center_x + math.cos(sub_angle) * sub_radius
                node_y = cluster_center_y + math.sin(sub_angle) * sub_radius

                random_role = random.choice(roles)
                node_num = str(id_counter).zfill(3)
                id_counter += 1
                agent_id = f"AG-{dept[:3].upper()}-{node_num}"

                rand_val = random.random()
                status = 'Active' if rand_val < 0.15 else ('Blocked' if rand_val < 0.20 else 'Idle')

                cpu = random.randint(40, 90) if status == 'Active' else (0 if status == 'Blocked' else random.randint(2, 10))
                mem = random.randint(50, 80) if status == 'Active' else (98 if status == 'Blocked' else random.randint(10, 30))
                lat = random.randint(2, 14) if status == 'Active' else (999 if status == 'Blocked' else random.randint(8, 18))

                self.agents.append({
                    "id": agent_id,
                    "name": f"SwarmUnit-{dept}-{node_num}",
                    "role": random_role,
                    "department": dept,
                    "status": status,
                    "mission": missions_by_dept[dept][i % len(missions_by_dept[dept])],
                    "toolScopes": [tools_by_dept[dept][i % len(tools_by_dept[dept])], tools_by_dept[dept][(i + 1) % len(tools_by_dept[dept])]],
                    "metrics": {
                        "cpu": cpu,
                        "memory": mem,
                        "latency": lat,
                        "requestCount": random.randint(50, 550)
                    },
                    "telemetryLogs": [
                        f"Agent spawned in cluster: {dept}.",
                        f"Synchronizing dynamic policy: ArbiterOS-{dept.upper()}-SECURE v5.0.2."
                    ],
                    "x": node_x,
                    "y": node_y
                })

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
        """Simulates real background noise and telemetry ticks from the 105 active agents"""
        # Minor adjustments to keep the UI feeling "alive" with background CPU noise
        active_agents = [a for a in self.agents if a["status"] == "Active"]
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
        while self.is_running:
            try:
                self.background_tick()
            except Exception as e:
                print(f"[TerminalStateManager] Tick error: {e}")
            await asyncio.sleep(2.0)

    async def broadcast(self, event_data: dict):
        import json
        payload = json.dumps(event_data)
        for q in self.subscribers:
            try:
                q.put_nowait(payload)
            except Exception:
                pass

# Global singleton
terminal_state_manager = TerminalStateManager()
