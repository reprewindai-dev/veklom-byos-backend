"""AI Agents Stack 2026 - Database Models for Six-Layer Architecture"""

from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from sqlalchemy import Column, String, Text, DateTime, JSON, Integer, Float, Boolean, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


# Layer 1: Models and Routers
class LLMRouter(Base):
    """LLM model routing configuration for agents"""
    __tablename__ = "llm_routers"
    
    id = Column(String, primary_key=True)
    workspace_id = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    
    # Routing configuration
    primary_model = Column(String, nullable=False)  # gpt-4, claude-3, gemini-pro
    fallback_models = Column(JSON, default=list)  # List of fallback models
    routing_strategy = Column(String, default="simple")  # simple, cost, latency, capability
    
    # Model-specific settings
    max_tokens = Column(Integer, default=4096)
    temperature = Column(Float, default=0.7)
    top_p = Column(Float, default=1.0)
    
    # Cost and performance tracking
    cost_per_1k_tokens = Column(Float)
    avg_latency_ms = Column(Float)
    reliability_score = Column(Float, default=1.0)
    
    # Status and metadata
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    agents = relationship("Agent", back_populates="router")


# Layer 2: Protocols and Tools (MCP Support)
class MCPTool(Base):
    """Model Context Protocol tool registration"""
    __tablename__ = "mcp_tools"
    
    id = Column(String, primary_key=True)
    workspace_id = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    
    # MCP protocol details
    tool_type = Column(String, nullable=False)  # filesystem, database, api, browser, etc.
    protocol_version = Column(String, default="2024-11-05")
    endpoint_url = Column(String)
    authentication = Column(JSON)  # API keys, OAuth, etc.
    
    # Tool schema
    input_schema = Column(JSON, nullable=False)  # JSON Schema for inputs
    output_schema = Column(JSON)  # Expected output format
    
    # Security and permissions
    required_permissions = Column(JSON, default=list)
    safety_level = Column(String, default="safe")  # safe, restricted, dangerous
    
    # Usage tracking
    usage_count = Column(Integer, default=0)
    last_used = Column(DateTime)
    error_rate = Column(Float, default=0.0)
    
    # Status
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class MCPConnection(Base):
    """MCP server connection and session management"""
    __tablename__ = "mcp_connections"
    
    id = Column(String, primary_key=True)
    workspace_id = Column(String, nullable=False, index=True)
    server_name = Column(String, nullable=False)
    server_endpoint = Column(String, nullable=False)
    
    # Connection state
    status = Column(String, default="disconnected")  # connected, disconnected, error
    last_ping = Column(DateTime)
    connection_config = Column(JSON)
    
    # Security
    client_id = Column(String)
    client_secret = Column(String)
    server_capabilities = Column(JSON)
    
    # Session management
    session_id = Column(String)
    session_expires = Column(DateTime)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# Layer 3: Memory and Context
class AgentMemory(Base):
    """Agent memory and context storage"""
    __tablename__ = "agent_memories"
    
    id = Column(String, primary_key=True)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False, index=True)
    workspace_id = Column(String, nullable=False, index=True)
    
    # Memory types
    memory_type = Column(String, nullable=False)  # episodic, semantic, procedural, working
    content = Column(Text, nullable=False)
    memory_metadata = Column(JSON)
    
    # Temporal and retrieval
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)
    access_count = Column(Integer, default=0)
    last_accessed = Column(DateTime)
    
    # Vector embedding for semantic search
    embedding_id = Column(String)  # Reference to vector database
    relevance_score = Column(Float)
    
    # Relationships
    agent = relationship("Agent", back_populates="memories")


class ConversationContext(Base):
    """Multi-turn conversation context for agents"""
    __tablename__ = "conversation_contexts"
    
    id = Column(String, primary_key=True)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False, index=True)
    workspace_id = Column(String, nullable=False, index=True)
    user_id = Column(String, nullable=False, index=True)
    
    # Conversation state
    session_id = Column(String, nullable=False, index=True)
    turn_number = Column(Integer, default=1)
    context_window = Column(JSON)  # Rolling window of recent messages
    
    # Context management
    summary = Column(Text)  # Compressed context for long conversations
    key_entities = Column(JSON)  # Extracted entities and relationships
    intent_history = Column(JSON)  # Track intent changes over time
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    agent = relationship("Agent", back_populates="conversations")


# Layer 4: Frameworks and Runtimes
class Agent(Base):
    """Core agent definition and runtime configuration"""
    __tablename__ = "agents"
    
    id = Column(Integer, primary_key=True)
    workspace_id = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    
    # Framework integration
    framework_type = Column(String, nullable=False)  # openai_sdk, google_adk, langgraph, custom
    framework_version = Column(String)
    
    # Agent configuration
    system_prompt = Column(Text, nullable=False)
    capabilities = Column(JSON, default=list)  # List of agent capabilities
    constraints = Column(JSON, default=dict)  # Agent constraints and rules
    
    # Runtime settings
    max_execution_time = Column(Integer, default=300)  # seconds
    max_tool_calls = Column(Integer, default=10)
    retry_policy = Column(JSON)
    
    # Model routing
    router_id = Column(String, ForeignKey("llm_routers.id"))
    
    # Status and metrics
    status = Column(String, default="active")  # active, inactive, error
    total_executions = Column(Integer, default=0)
    success_rate = Column(Float, default=0.0)
    avg_execution_time = Column(Float, default=0.0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    router = relationship("LLMRouter", back_populates="agents")
    memories = relationship("AgentMemory", back_populates="agent")
    conversations = relationship("ConversationContext", back_populates="agent")
    executions = relationship("AgentExecution", back_populates="agent")
    evaluations = relationship("AgentEvaluation", back_populates="agent")


class AgentExecution(Base):
    """Individual agent execution records"""
    __tablename__ = "agent_executions"
    
    id = Column(String, primary_key=True)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False, index=True)
    workspace_id = Column(String, nullable=False, index=True)
    session_id = Column(String, nullable=False, index=True)
    
    # Execution details
    input_data = Column(JSON, nullable=False)
    output_data = Column(JSON)
    execution_plan = Column(JSON)  # Step-by-step execution plan
    
    # Performance metrics
    started_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime)
    duration_ms = Column(Integer)
    tokens_used = Column(Integer)
    cost_estimate = Column(Float)
    
    # Tool usage
    tools_used = Column(JSON, default=list)
    tool_calls_count = Column(Integer, default=0)
    
    # Status and errors
    status = Column(String, default="running")  # running, completed, failed, cancelled
    error_message = Column(Text)
    error_type = Column(String)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    agent = relationship("Agent", back_populates="executions")


# Layer 5: Evaluation and Observability
class AgentEvaluation(Base):
    """Agent performance evaluation results"""
    __tablename__ = "agent_evaluations"
    
    id = Column(String, primary_key=True)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False, index=True)
    workspace_id = Column(String, nullable=False, index=True)
    evaluation_type = Column(String, nullable=False)  # offline, online, safety, performance
    
    # Evaluation configuration
    test_dataset = Column(String)  # Reference to test dataset
    evaluation_metrics = Column(JSON, nullable=False)  # Metrics being evaluated
    baseline_score = Column(Float)  # Previous score for comparison
    
    # Results
    overall_score = Column(Float, nullable=False)
    metric_scores = Column(JSON)  # Individual metric scores
    detailed_results = Column(JSON)  # Full evaluation results
    
    # Analysis
    failure_cases = Column(JSON, default=list)
    improvement_suggestions = Column(JSON, default=list)
    
    # Metadata
    evaluated_at = Column(DateTime, default=datetime.utcnow)
    evaluation_version = Column(String)
    
    # Relationships
    agent = relationship("Agent", back_populates="evaluations")


class AgentTrace(Base):
    """Detailed execution traces for observability"""
    __tablename__ = "agent_traces"
    
    id = Column(String, primary_key=True)
    execution_id = Column(String, ForeignKey("agent_executions.id"), nullable=False, index=True)
    agent_id = Column(Integer, nullable=False, index=True)
    workspace_id = Column(String, nullable=False, index=True)
    
    # Trace data
    trace_type = Column(String, nullable=False)  # llm_call, tool_call, memory_access, decision
    timestamp = Column(DateTime, default=datetime.utcnow)
    duration_ms = Column(Integer)
    
    # Detailed trace information
    input_data = Column(JSON)
    output_data = Column(JSON)
    memory_metadata = Column(JSON)
    
    # Performance indicators
    success = Column(Boolean)
    error_message = Column(Text)
    
    # Parent-child relationships for nested traces
    parent_trace_id = Column(String, ForeignKey("agent_traces.id"))
    child_traces = Column(JSON, default=list)  # List of child trace IDs


# Layer 6: Guardrails and Safety
class AgentGuardrail(Base):
    """Safety and compliance guardrails for agents"""
    __tablename__ = "agent_guardrails"
    
    id = Column(String, primary_key=True)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False, index=True)
    workspace_id = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    
    # Guardrail configuration
    guardrail_type = Column(String, nullable=False)  # input_filter, output_filter, tool_guard, rate_limit
    severity = Column(String, default="warning")  # info, warning, error, critical
    
    # Rules and conditions
    rules = Column(JSON, nullable=False)  # List of rules and conditions
    actions = Column(JSON, nullable=False)  # Actions to take when triggered
    
    # Status and metrics
    is_active = Column(Boolean, default=True)
    trigger_count = Column(Integer, default=0)
    last_triggered = Column(DateTime)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SafetyIncident(Base):
    """Record of safety and security incidents"""
    __tablename__ = "safety_incidents"
    
    id = Column(String, primary_key=True)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False, index=True)
    workspace_id = Column(String, nullable=False, index=True)
    execution_id = Column(String, ForeignKey("agent_executions.id"), index=True)
    
    # Incident details
    incident_type = Column(String, nullable=False)  # policy_violation, security_breach, error, abuse
    severity = Column(String, nullable=False)  # low, medium, high, critical
    
    # Description and context
    description = Column(Text, nullable=False)
    context_data = Column(JSON)  # Full context when incident occurred
    
    # Detection and response
    detected_by = Column(String)  # guardrail_id, user_report, system_monitor
    response_action = Column(String)  # blocked, logged, alerted, shutdown
    resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime)
    
    # Impact assessment
    impact_score = Column(Float)
    affected_users = Column(JSON, default=list)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# Multi-agent orchestration
class AgentSwarm(Base):
    """Multi-agent swarm orchestration"""
    __tablename__ = "agent_swarms"
    
    id = Column(String, primary_key=True)
    workspace_id = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    
    # Swarm configuration
    orchestration_pattern = Column(String, nullable=False)  # hierarchical, flat, dynamic
    communication_protocol = Column(String, default="mcp")  # mcp, custom, message_queue
    
    # Agent composition
    agent_ids = Column(JSON, nullable=False)  # List of agent IDs in the swarm
    roles = Column(JSON)  # Role assignments for each agent
    
    # Coordination settings
    coordination_rules = Column(JSON)
    conflict_resolution = Column(JSON)
    debate_protocol = Column(String, default="consensus") # consensus, supervisor, majority
    max_iterations = Column(Integer, default=3)
    
    # Status and metrics
    status = Column(String, default="active")
    total_tasks = Column(Integer, default=0)
    completed_tasks = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# Indexes for performance
Index('idx_agent_executions_agent_session', 'agent_id', 'session_id')
Index('idx_agent_memories_agent_type', 'agent_id', 'memory_type')
Index('idx_safety_incidents_agent_severity', 'agent_id', 'severity')
Index('idx_mcp_tools_workspace_active', 'workspace_id', 'is_active')
