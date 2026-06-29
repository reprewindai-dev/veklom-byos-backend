"""Sovereign service layer for Veklom Mission Lock / Policy Inertia behavior governance."""

import logging
import random
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timezone
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

# Import our unified DB models
from backend.db.models.mission_lock import (
    MissionDNA, AgentMission, MissionLockAgentState, EpisodeTelemetry, TeamState,
    CoordinationLog, RecoveryEvent, DNAAudit, AgentRuntimeState, AgentActionTrace,
    IdempotencyKey, RecoverySnapshot, MetricsCache, TenantRole, AuthzLog
)

logger = logging.getLogger(__name__)


class TabularPolicy:
    """Simple Q-learning policy using dict-based state-action values."""
    def __init__(self, actions: List[str], default_q: float = 0.0):
        self.actions = actions
        self.default_q = default_q
        self.q_table: Dict[str, Dict[str, float]] = {}

    def _ensure_state(self, state: str) -> None:
        if state not in self.q_table:
            self.q_table[state] = {a: self.default_q for a in self.actions}

    def value(self, state: str) -> float:
        self._ensure_state(state)
        return max(self.q_table[state].values()) if self.q_table[state] else self.default_q

    def best_action(self, state: str, valid_actions: Optional[List[str]] = None) -> str:
        self._ensure_state(state)
        candidates = valid_actions or self.actions
        values = {a: self.q_table[state].get(a, self.default_q) for a in candidates}
        if not values:
            return random.choice(self.actions)
        best = max(values.values())
        ties = [a for a, v in values.items() if v == best]
        return random.choice(ties) if ties else random.choice(candidates)

    def random_action(self, valid_actions: Optional[List[str]] = None) -> str:
        candidates = valid_actions or self.actions
        return random.choice(candidates) if candidates else random.choice(self.actions)

    def update(self, state: str, action: str, reward: float, next_state: str, lr: float, gamma: float = 0.95) -> None:
        self._ensure_state(state)
        self._ensure_state(next_state)
        td_target = reward + gamma * self.value(next_state)
        td_error = td_target - self.q_table[state][action]
        self.q_table[state][action] += lr * td_error

    def serialize(self) -> Dict[str, Any]:
        return {"q_table": self.q_table, "actions": self.actions}

    @classmethod
    def deserialize(cls, data: Dict[str, Any]) -> "TabularPolicy":
        policy = cls(actions=data["actions"])
        policy.q_table = data["q_table"]
        return policy


class MissionPath:
    """Defines the preferred action trajectory per state."""
    def __init__(self, preferred_actions: Dict[str, str]):
        self.preferred_actions = preferred_actions

    def expected_action(self, state: str) -> Optional[str]:
        return self.preferred_actions.get(state)

    def is_on_path(self, state: str, action: str) -> bool:
        return self.preferred_actions.get(state) == action


class MissionLockAgent:
    """Single agent with dual-policy architecture, reward shaping, and adaptive plasticity."""
    def __init__(
        self,
        agent_id: str,
        actions: List[str],
        dna: MissionDNA,
        mission: MissionPath,
    ):
        self.agent_id = agent_id
        self.actions = actions
        self.dna = dna
        self.mission = mission

        self.dominant_policy = TabularPolicy(actions)
        self.base_policy = TabularPolicy(actions)
        self.target_return: Optional[float] = None

    def valid_actions(self) -> List[str]:
        # Filter actions based on allowed / forbidden constraints
        candidates = self.dna.allowed_actions if self.dna.allowed_actions is not None else self.actions
        forbidden = self.dna.forbidden_actions or []
        return [a for a in candidates if a not in forbidden]

    def act(self, state: str, cue: bool = False) -> str:
        """Select action using dual-policy with mission bias.
        cue=True increases dominance temporarily (trigger-like behavior).
        """
        valid = self.valid_actions()
        expected = self.mission.expected_action(state)

        # Boost dominance on cues
        dominance = min(1.0, self.dna.dominance + (self.dna.cue_boost if cue else 0.0))

        # Prefer mission path with dominance probability
        if expected in valid and random.random() < dominance:
            return expected

        # Epsilon-exploration
        if random.random() < self.dna.epsilon:
            return self.base_policy.random_action(valid)

        # Otherwise, choose policy with higher expected value
        dom_action = self.dominant_policy.best_action(state, valid)
        base_action = self.base_policy.best_action(state, valid)

        if self.dominant_policy.value(state) >= self.base_policy.value(state):
            return dom_action
        return base_action

    def shaped_reward(self, state: str, action: str, base_reward: float) -> float:
        """Apply reward shaping: bonus for on-path, penalty for off-path, safety penalty."""
        reward = base_reward
        if self.mission.is_on_path(state, action):
            reward += self.dna.mission_bonus
        else:
            reward -= self.dna.off_path_penalty

        # Safety penalty for forbidden actions
        if action in (self.dna.forbidden_actions or []):
            reward -= 10.0 * self.dna.safety_weight

        return reward

    def update(self, state: str, action: str, reward: float, next_state: str) -> None:
        """Dual-policy update: base policy learns fast, dominant policy learns slow.
        Dominant policy only updates on positive advantage.
        """
        shaped = self.shaped_reward(state, action, reward)

        # Base policy learns quickly
        self.base_policy.update(state, action, shaped, next_state, lr=self.dna.base_learning_rate)

        # Dominant policy learns slowly (only on positive advantage)
        dominant_expected = self.dominant_policy.value(state)
        advantage = shaped - dominant_expected

        if advantage > 0:
            self.dominant_policy.update(
                state, action, shaped, next_state, lr=self.dna.plasticity
            )

    def adjust_rigidity(self, recent_returns: List[float], safety_event: bool = False) -> Tuple[bool, Optional[str]]:
        """Recovery logic: loosen rigidity (decrease dominance, increase exploration/plasticity) if performance degrades."""
        if not recent_returns:
            return False, None

        avg_return = sum(recent_returns) / len(recent_returns)

        if self.target_return is None:
            self.target_return = avg_return
            return False, None

        recovery_triggered = False
        reason = None

        if safety_event:
            reason = "safety_event"
            recovery_triggered = True
        elif avg_return < self.target_return * 0.8:
            reason = "performance_degradation"
            recovery_triggered = True

        if recovery_triggered:
            # Loosen dominance
            self.dna.dominance = max(
                self.dna.min_dominance, self.dna.dominance - 0.10
            )
            # Increase exploration
            self.dna.epsilon = min(
                self.dna.max_epsilon, self.dna.epsilon + 0.01
            )
            # Increase plasticity
            self.dna.plasticity = min(
                self.dna.max_plasticity, self.dna.plasticity * 1.5
            )
            logger.info(
                f"Agent {self.agent_id} recovery triggered: {reason}. "
                f"dominance={self.dna.dominance:.2f}, epsilon={self.dna.epsilon:.2f}, plasticity={self.dna.plasticity:.4f}"
            )

        return recovery_triggered, reason


class TeamCoordinator:
    """Coordinates individual agents in a team, shaping cooperation and safety."""
    def __init__(self, agents: Dict[str, MissionLockAgent]):
        self.agents = agents

    def cue_for_agent(self, agent: MissionLockAgent, team_phase: str, alerts: List[str]) -> bool:
        if "safety" in (alerts or []):
            return True
        if team_phase in {"dispatch", "verify", "recover", "critical"}:
            return True
        return False

    def coordination_bonus(
        self,
        agent: MissionLockAgent,
        action: str,
        team_phase: str,
        goal_progress: float,
    ) -> float:
        bonus = 0.0

        # Role-specific coordination rewards
        if agent.dna.role == "router" and action == "route_trusted":
            bonus += 0.5
        elif agent.dna.role == "planner" and action == "plan_conservative":
            bonus += 0.5
        elif agent.dna.role == "verifier" and action == "verify_strict":
            bonus += 0.75
        elif agent.dna.role == "executor" and action == "execute_safe":
            bonus += 1.0
        elif agent.dna.role == "watchdog" and action == "rollback":
            bonus += 1.5

        if goal_progress > 0.75:
            bonus += 0.25 * agent.dna.coordination_weight

        return bonus

    def safety_penalty(self, agent: MissionLockAgent, action: str, alerts: List[str]) -> float:
        if "safety" in (alerts or []) and action in {"execute_fast", "route_untrusted", "skip_verify"}:
            return -2.0 * agent.dna.safety_weight
        return 0.0

    def decide_joint_actions(
        self,
        state: str,
        team_phase: str,
        alerts: List[str],
    ) -> Dict[str, str]:
        actions = {}
        for agent_id, agent in self.agents.items():
            cue = self.cue_for_agent(agent, team_phase, alerts)
            actions[agent_id] = agent.act(state, cue=cue)
        return actions

    def update_team(
        self,
        state: str,
        next_state: str,
        joint_actions: Dict[str, str],
        env_rewards: Dict[str, float],
        team_phase: str,
        alerts: List[str],
        goal_progress: float,
    ) -> None:
        for agent_id, agent in self.agents.items():
            action = joint_actions[agent_id]
            local_reward = env_rewards.get(agent_id, 0.0)

            # Shapted reward: environment + coordination bonus + safety penalty
            coord_bonus = self.coordination_bonus(agent, action, team_phase, goal_progress)
            safety_penalty = self.safety_penalty(agent, action, alerts)
            total_reward = local_reward + coord_bonus + safety_penalty

            agent.update(state, action, total_reward, next_state)


class MissionLockService:
    """Core stateless service handling loading, saving, tracing, and metadata aggregation."""

    @staticmethod
    async def get_mission_dna(agent_id: str, db: AsyncSession) -> Optional[MissionDNA]:
        stmt = select(MissionDNA).where(MissionDNA.agent_id == agent_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def create_mission_dna(dna_data: Dict[str, Any], db: AsyncSession) -> MissionDNA:
        dna = MissionDNA(**dna_data)
        db.add(dna)
        await db.flush()
        return dna

    @staticmethod
    async def update_mission_dna(
        agent_id: str,
        updates: Dict[str, Any],
        changed_by: str,
        reason: str,
        db: AsyncSession
    ) -> Optional[MissionDNA]:
        dna = await MissionLockService.get_mission_dna(agent_id, db)
        if not dna:
            return None

        # Gather old values for auditing
        old_values = {}
        new_values = {}
        changed_fields = []

        for key, val in updates.items():
            if hasattr(dna, key):
                old_val = getattr(dna, key)
                if old_val != val:
                    old_values[key] = old_val
                    new_values[key] = val
                    changed_fields.append(key)
                    setattr(dna, key, val)

        if changed_fields:
            dna.version = (dna.version or 1) + 1
            dna.updated_at = datetime.now(timezone.utc)
            
            # Log to audit trail
            audit = DNAAudit(
                agent_id=agent_id,
                changed_fields=changed_fields,
                old_values=old_values,
                new_values=new_values,
                changed_by=changed_by,
                reason=reason,
                tenant_id=dna.tenant_id
            )
            db.add(audit)
            await db.flush()

        return dna

    @staticmethod
    async def get_agent_mission(agent_id: str, db: AsyncSession) -> Optional[AgentMission]:
        stmt = select(AgentMission).where(AgentMission.agent_id == agent_id, AgentMission.active == True)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def create_agent_mission(mission_data: Dict[str, Any], db: AsyncSession) -> AgentMission:
        # Deactivate any previous active mission paths
        stmt = select(AgentMission).where(AgentMission.agent_id == mission_data["agent_id"], AgentMission.active == True)
        result = await db.execute(stmt)
        for old_mission in result.scalars():
            old_mission.active = False

        mission = AgentMission(**mission_data)
        db.add(mission)
        await db.flush()
        return mission

    @staticmethod
    async def load_agent_state(
        agent_id: str,
        actions: List[str],
        db: AsyncSession
    ) -> Optional[MissionLockAgent]:
        """stateless load cycle reconstructing agent parameters & dual Q-tables out-of-process."""
        dna = await MissionLockService.get_mission_dna(agent_id, db)
        if not dna:
            logger.warning(f"DNA not found for agent {agent_id}. Cannot load.")
            return None

        mission_model = await MissionLockService.get_agent_mission(agent_id, db)
        if not mission_model:
            logger.warning(f"Active mission path not found for agent {agent_id}. Using empty path.")
            mission_path = MissionPath(preferred_actions={})
        else:
            mission_path = MissionPath(preferred_actions=mission_model.preferred_transitions)

        # Create the agent
        agent = MissionLockAgent(agent_id=agent_id, actions=actions, dna=dna, mission=mission_path)

        # 1. Load active adaptive parameter modifications from agent_state
        state_stmt = select(MissionLockAgentState).where(MissionLockAgentState.agent_id == agent_id)
        state_res = await db.execute(state_stmt)
        state = state_res.scalar_one_or_none()

        if state:
            agent.dna.dominance = state.current_dominance
            agent.dna.plasticity = state.current_plasticity
            agent.dna.epsilon = state.current_epsilon
            agent.target_return = state.target_return

        # 2. Load serialized TabularPolicy matrices from agent_runtime_state
        runtime_stmt = select(AgentRuntimeState).where(AgentRuntimeState.agent_id == agent_id)
        runtime_res = await db.execute(runtime_stmt)
        runtime = runtime_res.scalar_one_or_none()

        if runtime:
            agent.dominant_policy = TabularPolicy.deserialize(runtime.dominant_policy_json)
            agent.base_policy = TabularPolicy.deserialize(runtime.base_policy_json)
            agent.target_return = runtime.target_return

        return agent

    @staticmethod
    async def save_agent_state(
        agent: MissionLockAgent,
        db: AsyncSession,
        last_action: Optional[str] = None,
        last_state: Optional[str] = None,
        last_episode_return: float = 0.0,
        moving_avg_return: float = 0.0,
        path_conformance: float = 0.0,
        steps_since_recovery: int = 0,
        safety_violations: int = 0
    ) -> None:
        """stateless save cycle persisting parameters & serialized Q-learning policies out-of-process."""
        agent_id = agent.agent_id

        # 1. Save runtime serialization matrices (Q-tables)
        runtime_stmt = select(AgentRuntimeState).where(AgentRuntimeState.agent_id == agent_id)
        runtime_res = await db.execute(runtime_stmt)
        runtime = runtime_res.scalar_one_or_none()

        dominant_ser = agent.dominant_policy.serialize()
        base_ser = agent.base_policy.serialize()

        if not runtime:
            runtime = AgentRuntimeState(
                agent_id=agent_id,
                target_return=agent.target_return,
                dominant_policy_json=dominant_ser,
                base_policy_json=base_ser,
                last_update=datetime.now(timezone.utc)
            )
            db.add(runtime)
        else:
            runtime.target_return = agent.target_return
            runtime.dominant_policy_json = dominant_ser
            runtime.base_policy_json = base_ser
            runtime.last_update = datetime.now(timezone.utc)

        # 2. Update agent metric states in agent_state
        state_stmt = select(MissionLockAgentState).where(MissionLockAgentState.agent_id == agent_id)
        state_res = await db.execute(state_stmt)
        state = state_res.scalar_one_or_none()

        if not state:
            state = MissionLockAgentState(
                agent_id=agent_id,
                current_dominance=agent.dna.dominance,
                current_plasticity=agent.dna.plasticity,
                current_epsilon=agent.dna.epsilon,
                target_return=agent.target_return,
                last_episode_return=last_episode_return,
                moving_avg_return=moving_avg_return,
                path_conformance=path_conformance,
                steps_since_recovery=steps_since_recovery,
                safety_violations=safety_violations,
                last_action=last_action,
                last_state=last_state,
                last_update=datetime.now(timezone.utc)
            )
            db.add(state)
        else:
            state.current_dominance = agent.dna.dominance
            state.current_plasticity = agent.dna.plasticity
            state.current_epsilon = agent.dna.epsilon
            state.target_return = agent.target_return
            state.last_episode_return = last_episode_return
            state.moving_avg_return = moving_avg_return
            state.path_conformance = path_conformance
            state.steps_since_recovery = steps_since_recovery
            state.safety_violations = safety_violations
            if last_action:
                state.last_action = last_action
            if last_state:
                state.last_state = last_state
            state.last_update = datetime.now(timezone.utc)

        await db.flush()

    @staticmethod
    async def record_action_trace(
        agent_id: str,
        state: str,
        action: str,
        reward: float,
        next_state: str,
        on_path: bool,
        cue: bool,
        tenant_id: Optional[str],
        db: AsyncSession
    ) -> None:
        trace = AgentActionTrace(
            agent_id=agent_id,
            state=state,
            action=action,
            reward=reward,
            next_state=next_state,
            on_path=on_path,
            cue=cue,
            timestamp=datetime.now(timezone.utc),
            tenant_id=tenant_id
        )
        db.add(trace)
        await db.flush()

    @staticmethod
    async def record_episode_telemetry(
        telemetry_data: Dict[str, Any],
        db: AsyncSession
    ) -> EpisodeTelemetry:
        telemetry = EpisodeTelemetry(**telemetry_data)
        db.add(telemetry)
        await db.flush()
        return telemetry

    @staticmethod
    async def record_recovery_event(
        agent: MissionLockAgent,
        episode_num: int,
        trigger: str,
        reason: str,
        dominance_before: float,
        epsilon_before: float,
        plasticity_before: float,
        db: AsyncSession
    ) -> RecoveryEvent:
        event = RecoveryEvent(
            agent_id=agent.agent_id,
            episode_num=episode_num,
            trigger=trigger,
            reason=reason,
            dominance_before=dominance_before,
            dominance_after=agent.dna.dominance,
            epsilon_before=epsilon_before,
            epsilon_after=agent.dna.epsilon,
            plasticity_before=plasticity_before,
            plasticity_after=agent.dna.plasticity,
            timestamp=datetime.now(timezone.utc),
            tenant_id=agent.dna.tenant_id
        )
        db.add(event)
        await db.flush()

        # Capture complete instant snapshot of policies and parameters
        snapshot = RecoverySnapshot(
            agent_id=agent.agent_id,
            recovery_event_id=event.id,
            state_snapshot={
                "dominance": agent.dna.dominance,
                "epsilon": agent.dna.epsilon,
                "plasticity": agent.dna.plasticity,
                "target_return": agent.target_return,
                "dominant_policy": agent.dominant_policy.serialize(),
                "base_policy": agent.base_policy.serialize()
            },
            timestamp=datetime.now(timezone.utc)
        )
        db.add(snapshot)
        await db.flush()

        return event

    @staticmethod
    async def get_agent_metrics(agent_id: str, db: AsyncSession) -> Dict[str, Any]:
        """Aggregate recent metrics for an agent."""
        # Query total episodes, conformance, and safety events
        episodes_stmt = select(
            func.count(EpisodeTelemetry.id).label("total_episodes"),
            func.avg(EpisodeTelemetry.episode_return).label("avg_return"),
            func.avg(EpisodeTelemetry.path_conformance).label("avg_conformance"),
            func.sum(EpisodeTelemetry.safety_events).label("total_safety_events")
        ).where(EpisodeTelemetry.agent_id == agent_id)
        
        episodes_res = await db.execute(episodes_stmt)
        ep_row = episodes_res.fetchone()

        recovery_stmt = select(func.count(RecoveryEvent.id)).where(RecoveryEvent.agent_id == agent_id)
        recovery_res = await db.execute(recovery_stmt)
        recovery_count = recovery_res.scalar_or_none() or 0

        return {
            "total_episodes": ep_row[0] or 0,
            "avg_return": float(ep_row[1] or 0.0),
            "avg_conformance": float(ep_row[2] or 0.0),
            "total_safety_events": ep_row[3] or 0,
            "recovery_count": recovery_count
        }

    @staticmethod
    async def get_global_metrics(db: AsyncSession) -> Dict[str, Any]:
        # Cache-bypass real-time analytics aggregation
        agent_count_stmt = select(func.count(MissionDNA.id))
        agent_count_res = await db.execute(agent_count_stmt)
        total_agents = agent_count_res.scalar_or_none() or 0

        state_stmt = select(
            func.avg(MissionLockAgentState.current_dominance).label("avg_dominance"),
            func.avg(MissionLockAgentState.path_conformance).label("avg_conformance"),
            func.sum(MissionLockAgentState.safety_violations).label("total_safety_violations")
        )
        state_res = await db.execute(state_stmt)
        state_row = state_res.fetchone()

        recovery_stmt = select(func.count(RecoveryEvent.id))
        recovery_res = await db.execute(recovery_stmt)
        total_recoveries = recovery_res.scalar_or_none() or 0

        return {
            "total_agents": total_agents,
            "agents_in_recovery": total_recoveries,  # Simple dynamic mapping
            "avg_dominance": float(state_row[0] or 0.85),
            "avg_path_conformance": float(state_row[1] or 0.0),
            "total_safety_violations": int(state_row[2] or 0),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    @staticmethod
    async def check_idempotency(key: str, db: AsyncSession) -> Optional[Dict[str, Any]]:
        stmt = select(IdempotencyKey).where(IdempotencyKey.key == key)
        result = await db.execute(stmt)
        row = result.scalar_one_or_none()
        return row.response_json if row else None

    @staticmethod
    async def save_idempotency(key: str, response: Dict[str, Any], db: AsyncSession) -> None:
        # Check if already exists to prevent duplicate insert errors
        existing = await MissionLockService.check_idempotency(key, db)
        if not existing:
            row = IdempotencyKey(key=key, response_json=response, created_at=datetime.now(timezone.utc))
            db.add(row)
            await db.flush()

    @staticmethod
    async def get_dna_audit_log(agent_id: str, limit: int, db: AsyncSession) -> List[DNAAudit]:
        stmt = select(DNAAudit).where(DNAAudit.agent_id == agent_id).order_by(DNAAudit.timestamp.desc()).limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def continuous_authz_gate(
        user_id: str,
        tenant_id: str,
        action: str,
        resource: str,
        db: AsyncSession
    ) -> Tuple[bool, str]:
        """Continuous Zero-Trust authorization checking."""
        # Query role in tenant_roles
        stmt = select(TenantRole).where(TenantRole.tenant_id == tenant_id, TenantRole.user_id == user_id)
        result = await db.execute(stmt)
        role_row = result.scalar_one_or_none()

        decision = "DENIED"
        reason = "No role assigned in this tenant"

        if role_row:
            role = role_row.role.upper()
            if role in {"OWNER", "ADMIN"}:
                decision = "GRANTED"
                reason = "Owner/Admin level continuous clearance"
            elif role == "ANALYST":
                if action in {"READ", "GET", "LIST"}:
                    decision = "GRANTED"
                    reason = "Analyst read-only clearance"
                else:
                    reason = "Analyst write operation denied"
            elif role in {"USER", "READONLY"}:
                if action in {"READ", "GET"} and "dna" in resource:
                    decision = "GRANTED"
                    reason = "User read-only clearance"
                else:
                    reason = "Standard user unauthorized for this operation"

        # Log to authz log
        log = AuthzLog(
            user_id=user_id,
            tenant_id=tenant_id,
            action=action,
            resource=resource,
            decision=decision,
            reason=reason,
            timestamp=datetime.now(timezone.utc)
        )
        db.add(log)
        return (decision == "GRANTED"), reason

    @staticmethod
    async def extract_and_register_gpc_constraints(
        pipeline_id: str,
        name: Optional[str],
        description: Optional[str],
        nodes: List[Any],
        tenant_id: str,
        db: AsyncSession
    ) -> None:
        """Analyze a compiled GPC pipeline's metadata/nodes to generate behavioral DNA and paths."""
        role = "executor"
        if name:
            name_lower = name.lower()
            if "planner" in name_lower:
                role = "planner"
            elif "router" in name_lower:
                role = "router"
            elif "verify" in name_lower or "check" in name_lower:
                role = "verifier"
            elif "watch" in name_lower or "monitor" in name_lower:
                role = "watchdog"

        forbidden_actions = []
        preferred_transitions = {}

        if description:
            desc_lower = description.lower()
            if "forbidden:" in desc_lower:
                parts = desc_lower.split("forbidden:")
                if len(parts) > 1:
                    subparts = parts[1].split(".")
                    for act in subparts[0].split(","):
                        cleaned = act.strip()
                        if cleaned:
                            forbidden_actions.append(cleaned)
            
            if "prefer:" in desc_lower:
                parts = desc_lower.split("prefer:")
                if len(parts) > 1:
                    subparts = parts[1].split(".")
                    for trans in subparts[0].split(","):
                        if "->" in trans:
                            st_act = trans.split("->")
                            if len(st_act) == 2:
                                st = st_act[0].strip()
                                ac = st_act[1].strip()
                                if st and ac:
                                    preferred_transitions[st] = ac

        # Analyze nodes configuration
        for node in nodes:
            if hasattr(node, "config") and node.config:
                if "forbidden_actions" in node.config:
                    if isinstance(node.config["forbidden_actions"], list):
                        forbidden_actions.extend([str(a) for a in node.config["forbidden_actions"]])
                if "preferred_transitions" in node.config:
                    if isinstance(node.config["preferred_transitions"], dict):
                        preferred_transitions.update(node.config["preferred_transitions"])

        if not forbidden_actions:
            forbidden_actions = ["bypass_verification", "exceed_budget_limit", "unauthorized_data_egress"]

        if not preferred_transitions:
            preferred_transitions = {
                "idle": "fetch_task",
                "task_received": "verify_budget",
                "budget_ok": "execute_task",
                "task_executed": "validate_output",
                "validation_passed": "commit_results"
            }

        forbidden_actions = list(set(forbidden_actions))

        # 1. Register or update the Mission DNA
        stmt = select(MissionDNA).where(MissionDNA.agent_id == pipeline_id)
        res = await db.execute(stmt)
        dna = res.scalar_one_or_none()

        if not dna:
            dna = MissionDNA(
                agent_id=pipeline_id,
                tenant_id=tenant_id,
                role=role,
                dominance=0.85,
                plasticity=0.01,
                base_learning_rate=0.08,
                epsilon=0.02,
                mission_bonus=1.0,
                off_path_penalty=0.15,
                coordination_weight=0.5,
                safety_weight=1.0,
                cue_boost=0.10,
                min_dominance=0.5,
                max_epsilon=0.15,
                max_plasticity=0.05,
                allowed_actions=["fetch_task", "verify_budget", "execute_task", "validate_output", "commit_results", "escalate", "idle", "bypass_verification", "exceed_budget_limit", "unauthorized_data_egress"],
                forbidden_actions=forbidden_actions,
                locked=False,
                version=1,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            db.add(dna)
        else:
            dna.role = role
            dna.forbidden_actions = list(set(dna.forbidden_actions + forbidden_actions))
            dna.updated_at = datetime.now(timezone.utc)

        # 2. Register Agent Mission path
        mission_stmt = select(AgentMission).where(AgentMission.agent_id == pipeline_id, AgentMission.active == True)
        mission_res = await db.execute(mission_stmt)
        for am in mission_res.scalars():
            am.active = False

        mission = AgentMission(
            agent_id=pipeline_id,
            tenant_id=tenant_id,
            mission_name=f"GPC Conformance Path for {name or 'Pipeline'}",
            preferred_transitions=preferred_transitions,
            active=True,
            version=1,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        db.add(mission)

        # 3. Save initial agent runtime state
        state_stmt = select(MissionLockAgentState).where(MissionLockAgentState.agent_id == pipeline_id)
        state_res = await db.execute(state_stmt)
        state = state_res.scalar_one_or_none()

        if not state:
            state = MissionLockAgentState(
                agent_id=pipeline_id,
                current_dominance=0.85,
                current_plasticity=0.01,
                current_epsilon=0.02,
                target_return=None,
                path_conformance=1.0,
                last_update=datetime.now(timezone.utc)
            )
            db.add(state)

        # 4. Save initial Q-tables
        runtime_stmt = select(AgentRuntimeState).where(AgentRuntimeState.agent_id == pipeline_id)
        runtime_res = await db.execute(runtime_stmt)
        runtime = runtime_res.scalar_one_or_none()

        if not runtime:
            actions = ["fetch_task", "verify_budget", "execute_task", "validate_output", "commit_results", "escalate", "idle", "bypass_verification", "exceed_budget_limit", "unauthorized_data_egress"]
            empty_q = {"q_table": {}, "actions": actions}
            runtime = AgentRuntimeState(
                agent_id=pipeline_id,
                dominant_policy_json=empty_q,
                base_policy_json=empty_q,
                target_return=None,
                last_update=datetime.now(timezone.utc)
            )
            db.add(runtime)

        await db.flush()
        logger.info(f"Registered newborn agent constraints for GPC compiled pipeline {pipeline_id} under tenant {tenant_id}")

