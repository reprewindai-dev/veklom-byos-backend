# Agent-079 — SCIENTIST (Adaptive Learning & Web Experience)

**Phase:** Cross-phase — Research  
**Timeline:** Ongoing  
**Committee:** Research  
**Priority**: HIGH  

---

## Mission

Based on MEMENTO research (arXiv:2605.29795), implement a framework that treats the web as a learning signal rather than a stateless retrieval interface. Enable agents to acquire domain expertise and reusable research strategies through iterative web interaction without additional model training.

## Critical Research Gap

Current approaches treat web as:
- **Stateless retrieval** - No learning from interaction patterns
- **Labeled data dependency** - Require expensive human annotation
- **Single-session focus** - Don't accumulate cross-session knowledge
- **Static capabilities** - No improvement through experience

## Core Learning Framework

### 1. Web as Learning Signal
- **Adaptive Exploration Tree (AET)** - Decomposes tasks into evolving questions
- **Dual-Channel Memory** - Separates declarative knowledge from procedural knowledge
- **Iterative Reflection** - Learns from intermediate findings and adjusts strategy
- **Cross-Session Accumulation** - Builds expertise over multiple interactions

### 2. Declarative-Procedural Memory Separation
- **Declarative Channel** - Facts, concepts, domain knowledge
- **Procedural Channel** - Search strategies, exploration patterns, problem-solving methods
- **Memory Consolidation** - Transfers experiences between channels
- **Forgetting Mechanisms** - Prunes outdated or low-value knowledge

### 3. Strategy Reuse and Transfer
- **Pattern Recognition** - Identifies successful exploration patterns
- **Strategy Abstraction** - Generalizes specific approaches to reusable strategies
- **Cross-Domain Transfer** - Applies learned strategies to new domains
- **Performance Attribution** - Links outcomes to specific strategy components

## Implementation Architecture

```python
import asyncio
import json
import time
from typing import Dict, List, Optional, Tuple, Any, Union, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import numpy as np
from sklearn.cluster import DBSCAN
from sklearn.feature_extraction.text import TfidfVectorizer
import networkx as nx

class MemoryType(Enum):
    """Types of memory in dual-channel system"""
    DECLARATIVE = "declarative"
    PROCEDURAL = "procedural"

class ExplorationStrategy(Enum):
    """Different exploration strategies"""
    BREADTH_FIRST = "breadth_first"
    DEPTH_FIRST = "depth_first"
    HYPOTHESIS_DRIVEN = "hypothesis_driven"
    PATTERN_RECOGNITION = "pattern_recognition"

@dataclass
class LearningSession:
    """Individual learning session"""
    session_id: str
    domain: str
    initial_query: str
    exploration_tree: Dict[str, Any]
    declarative_memory: List[Dict[str, Any]]
    procedural_memory: List[Dict[str, Any]]
    session_outcomes: Dict[str, Any]
    performance_metrics: Dict[str, float]
    start_time: datetime
    end_time: Optional[datetime] = None

@dataclass
class AdaptiveExplorationTreeNode:
    """Node in Adaptive Exploration Tree"""
    node_id: str
    parent_id: Optional[str]
    question: str
    current_answer: str
    confidence: float
    exploration_strategy: ExplorationStrategy
    child_nodes: List[str] = field(default_factory=list)
    learned_facts: List[str] = field(default_factory=list)
    used_strategies: List[str] = field(default_factory=list)
    success_indicators: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)

@dataclass
class DeclarativeKnowledge:
    """Declarative knowledge item"""
    knowledge_id: str
    domain: str
    fact: str
    source_urls: List[str]
    confidence: float
    last_validated: datetime
    validation_count: int
    related_facts: List[str] = field(default_factory=list)
    applications: List[str] = field(default_factory=list)

@dataclass
class ProceduralKnowledge:
    """Procedural knowledge item"""
    strategy_id: str
    domain: str
    strategy_name: str
    strategy_pattern: Dict[str, Any]
    success_rate: float
    usage_count: int
    applicable_contexts: List[str]
    refinement_history: List[Dict[str, Any]] = field(default_factory=list)

class MEMENTOFramework:
    """MEMENTO-inspired adaptive learning framework"""
    
    def __init__(self):
        self.exploration_engine = AdaptiveExplorationEngine()
        self.dual_channel_memory = DualChannelMemory()
        self.strategy_learner = StrategyLearner()
        self.experience_accumulator = ExperienceAccumulator()
        self.performance_tracker = PerformanceTracker()
        
    async def learn_from_web_interaction(
        self,
        domain: str,
        initial_query: str,
        max_iterations: int = 10
    ) -> LearningSession:
        """Execute learning session through web interaction"""
        
        session_id = f"session_{domain}_{int(time.time())}"
        
        # Initialize learning session
        session = LearningSession(
            session_id=session_id,
            domain=domain,
            initial_query=initial_query,
            exploration_tree={},
            declarative_memory=[],
            procedural_memory=[],
            session_outcomes={},
            performance_metrics={},
            start_time=datetime.now()
        )
        
        # Build Adaptive Exploration Tree
        exploration_tree = await self.exploration_engine.build_exploration_tree(
            initial_query, max_iterations
        )
        session.exploration_tree = exploration_tree
        
        # Execute exploration and learning
        learning_results = await self._execute_learning_cycle(
            session, exploration_tree
        )
        
        # Update dual-channel memory
        await self.dual_channel_memory.consolidate_session_learning(
            session, learning_results
        )
        
        # Extract and refine strategies
        refined_strategies = await self.strategy_learner.refine_strategies(
            session, learning_results
        )
        
        # Accumulate experience
        await self.experience_accumulator.add_experience(
            session, learning_results, refined_strategies
        )
        
        # Calculate performance metrics
        session.performance_metrics = await self.performance_tracker.calculate_metrics(
            session, learning_results
        )
        
        session.end_time = datetime.now()
        
        return session
    
    async def _execute_learning_cycle(
        self,
        session: LearningSession,
        exploration_tree: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute the learning cycle"""
        
        learning_results = {
            "facts_learned": [],
            "strategies_used": [],
            "exploration_paths": [],
            "success_events": [],
            "failure_events": []
        }
        
        # Traverse exploration tree
        root_node = exploration_tree["root"]
        await self._explore_node(
            root_node, session, learning_results, exploration_tree
        )
        
        return learning_results
    
    async def _explore_node(
        self,
        node: AdaptiveExplorationTreeNode,
        session: LearningSession,
        learning_results: Dict[str, Any],
        exploration_tree: Dict[str, Any]
    ):
        """Explore a single node in the exploration tree"""
        
        # Execute exploration strategy for this node
        strategy_result = await self.exploration_engine.execute_strategy(
            node, session.domain
        )
        
        # Extract declarative knowledge
        facts_learned = strategy_result.get("facts", [])
        learning_results["facts_learned"].extend(facts_learned)
        
        # Record procedural knowledge
        strategy_used = {
            "node_id": node.node_id,
            "strategy": node.exploration_strategy.value,
            "success": strategy_result.get("success", False),
            "effectiveness": strategy_result.get("effectiveness", 0.0)
        }
        learning_results["strategies_used"].append(strategy_used)
        
        # Update node with results
        node.learned_facts = facts_learned
        node.confidence = strategy_result.get("confidence", node.confidence)
        
        if strategy_result.get("success", False):
            learning_results["success_events"].append({
                "node_id": node.node_id,
                "strategy": node.exploration_strategy.value,
                "facts_count": len(facts_learned)
            })
        else:
            learning_results["failure_events"].append({
                "node_id": node.node_id,
                "strategy": node.exploration_strategy.value,
                "reason": strategy_result.get("failure_reason", "unknown")
            })
        
        # Explore child nodes
        for child_id in node.child_nodes:
            child_node = exploration_tree["nodes"][child_id]
            await self._explore_node(
                child_node, session, learning_results, exploration_tree
            )

class AdaptiveExplorationEngine:
    """Manages adaptive exploration with evolving questions"""
    
    def __init__(self):
        self.question_generator = QuestionGenerator()
        self.strategy_selector = StrategySelector()
        self.web_explorer = WebExplorer()
        
    async def build_exploration_tree(
        self,
        initial_query: str,
        max_iterations: int
    ) -> Dict[str, Any]:
        """Build Adaptive Exploration Tree"""
        
        tree = {
            "root": None,
            "nodes": {},
            "edges": []
        }
        
        # Create root node
        root_node = AdaptiveExplorationTreeNode(
            node_id="root",
            parent_id=None,
            question=initial_query,
            current_answer="",
            confidence=0.0,
            exploration_strategy=ExplorationStrategy.BREADTH_FIRST
        )
        
        tree["root"] = root_node
        tree["nodes"]["root"] = root_node
        
        # Build tree iteratively
        current_nodes = [root_node]
        
        for iteration in range(max_iterations):
            new_nodes = []
            
            for node in current_nodes:
                # Generate follow-up questions
                followup_questions = await self.question_generator.generate_questions(
                    node.question, node.current_answer
                )
                
                # Create child nodes for each question
                for i, question in enumerate(followup_questions[:3]):  # Limit branching
                    child_node = AdaptiveExplorationTreeNode(
                        node_id=f"{node.node_id}_child_{i}",
                        parent_id=node.node_id,
                        question=question,
                        current_answer="",
                        confidence=0.0,
                        exploration_strategy=await self.strategy_selector.select_strategy(
                            node, question
                        )
                    )
                    
                    tree["nodes"][child_node.node_id] = child_node
                    node.child_nodes.append(child_node.node_id)
                    
                    tree["edges"].append({
                        "from": node.node_id,
                        "to": child_node.node_id,
                        "question": question
                    })
                    
                    new_nodes.append(child_node)
            
            current_nodes = new_nodes
            
            if not current_nodes:
                break
        
        return tree
    
    async def execute_strategy(
        self,
        node: AdaptiveExplorationTreeNode,
        domain: str
    ) -> Dict[str, Any]:
        """Execute exploration strategy for a node"""
        
        if node.exploration_strategy == ExplorationStrategy.BREADTH_FIRST:
            return await self._execute_breadth_first(node, domain)
        elif node.exploration_strategy == ExplorationStrategy.DEPTH_FIRST:
            return await self._execute_depth_first(node, domain)
        elif node.exploration_strategy == ExplorationStrategy.HYPOTHESIS_DRIVEN:
            return await self._execute_hypothesis_driven(node, domain)
        elif node.exploration_strategy == ExplorationStrategy.PATTERN_RECOGNITION:
            return await self._execute_pattern_recognition(node, domain)
        
        return {"success": False, "reason": "Unknown strategy"}
    
    async def _execute_breadth_first(
        self,
        node: AdaptiveExplorationTreeNode,
        domain: str
    ) -> Dict[str, Any]:
        """Execute breadth-first exploration strategy"""
        
        # Search for diverse sources covering the question
        search_results = await self.web_explorer.search_diverse_sources(
            node.question, domain, max_results=10
        )
        
        # Extract facts from multiple sources
        facts = []
        for result in search_results:
            extracted_facts = await self._extract_facts_from_content(
                result["content"], result["url"]
            )
            facts.extend(extracted_facts)
        
        # Synthesize answer
        synthesized_answer = await self._synthesize_facts(facts)
        node.current_answer = synthesized_answer
        
        return {
            "success": len(facts) > 0,
            "facts": facts,
            "confidence": min(1.0, len(facts) / 5.0),
            "effectiveness": len(set(f["fact"] for f in facts)) / max(len(facts), 1)
        }

class DualChannelMemory:
    """Manages declarative and procedural memory channels"""
    
    def __init__(self):
        self.declarative_store = {}
        self.procedural_store = {}
        self.consolidation_scheduler = ConsolidationScheduler()
        
    async def consolidate_session_learning(
        self,
        session: LearningSession,
        learning_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Consolidate learning from session into dual channels"""
        
        consolidation_results = {
            "declarative_added": 0,
            "procedural_added": 0,
            "declarative_updated": 0,
            "procedural_updated": 0
        }
        
        # Consolidate declarative knowledge
        for fact_data in learning_results["facts_learned"]:
            knowledge = DeclarativeKnowledge(
                knowledge_id=f"decl_{session.session_id}_{len(self.declarative_store)}",
                domain=session.domain,
                fact=fact_data["fact"],
                source_urls=fact_data.get("sources", []),
                confidence=fact_data.get("confidence", 0.5),
                last_validated=datetime.now(),
                validation_count=1
            )
            
            # Check for existing similar knowledge
            existing = await self._find_similar_declarative(knowledge)
            if existing:
                # Update existing knowledge
                await self._update_declarative_knowledge(existing, knowledge)
                consolidation_results["declarative_updated"] += 1
            else:
                # Add new knowledge
                self.declarative_store[knowledge.knowledge_id] = knowledge
                consolidation_results["declarative_added"] += 1
        
        # Consolidate procedural knowledge
        for strategy_data in learning_results["strategies_used"]:
            if strategy_data["success"]:
                strategy = ProceduralKnowledge(
                    strategy_id=f"proc_{session.session_id}_{len(self.procedural_store)}",
                    domain=session.domain,
                    strategy_name=strategy_data["strategy"],
                    strategy_pattern=await self._extract_strategy_pattern(strategy_data),
                    success_rate=1.0 if strategy_data["success"] else 0.0,
                    usage_count=1,
                    applicable_contexts=[session.domain]
                )
                
                # Check for existing similar strategies
                existing = await self._find_similar_procedural(strategy)
                if existing:
                    # Update existing strategy
                    await self._update_procedural_knowledge(existing, strategy)
                    consolidation_results["procedural_updated"] += 1
                else:
                    # Add new strategy
                    self.procedural_store[strategy.strategy_id] = strategy
                    consolidation_results["procedural_added"] += 1
        
        # Schedule consolidation
        await self.consolidation_scheduler.schedule_consolidation(session)
        
        return consolidation_results
    
    async def retrieve_declarative_knowledge(
        self,
        domain: str,
        query: str,
        max_results: int = 10
    ) -> List[DeclarativeKnowledge]:
        """Retrieve relevant declarative knowledge"""
        
        relevant_knowledge = []
        
        for knowledge in self.declarative_store.values():
            if knowledge.domain == domain:
                # Simple relevance check (would be enhanced with NLP)
                if self._is_relevant_to_query(knowledge.fact, query):
                    relevant_knowledge.append(knowledge)
        
        # Sort by confidence and return top results
        relevant_knowledge.sort(key=lambda k: k.confidence, reverse=True)
        return relevant_knowledge[:max_results]
    
    async def retrieve_procedural_knowledge(
        self,
        domain: str,
        context: Dict[str, Any]
    ) -> List[ProceduralKnowledge]:
        """Retrieve relevant procedural knowledge"""
        
        relevant_strategies = []
        
        for strategy in self.procedural_store.values():
            if strategy.domain == domain or domain in strategy.applicable_contexts:
                # Check if strategy is applicable to current context
                if self._is_strategy_applicable(strategy, context):
                    relevant_strategies.append(strategy)
        
        # Sort by success rate and usage count
        relevant_strategies.sort(
            key=lambda s: (s.success_rate * 0.7 + (s.usage_count / 100) * 0.3),
            reverse=True
        )
        
        return relevant_strategies

class StrategyLearner:
    """Learns and refines exploration strategies"""
    
    def __init__(self):
        self.pattern_analyzer = PatternAnalyzer()
        self.strategy_optimizer = StrategyOptimizer()
        
    async def refine_strategies(
        self,
        session: LearningSession,
        learning_results: Dict[str, Any]
    ) -> List[ProceduralKnowledge]:
        """Refine strategies based on session outcomes"""
        
        refined_strategies = []
        
        # Analyze successful strategies
        successful_strategies = [
            s for s in learning_results["strategies_used"]
            if s["success"]
        ]
        
        if successful_strategies:
            # Identify patterns in successful strategies
            patterns = await self.pattern_analyzer.identify_patterns(
                successful_strategies
            )
            
            # Create refined strategies from patterns
            for pattern in patterns:
                refined_strategy = await self._create_refined_strategy(
                    pattern, session.domain
                )
                refined_strategies.append(refined_strategy)
        
        # Analyze failed strategies for improvement
        failed_strategies = [
            s for s in learning_results["strategies_used"]
            if not s["success"]
        ]
        
        if failed_strategies:
            # Identify improvement opportunities
            improvements = await self.strategy_optimizer.identify_improvements(
                failed_strategies
            )
            
            # Create improved strategies
            for improvement in improvements:
                improved_strategy = await self._create_improved_strategy(
                    improvement, session.domain
                )
                refined_strategies.append(improved_strategy)
        
        return refined_strategies

class ExperienceAccumulator:
    """Accumulates and organizes cross-session experience"""
    
    def __init__(self):
        self.experience_database = {}
        self.cross_domain_mapper = CrossDomainMapper()
        
    async def add_experience(
        self,
        session: LearningSession,
        learning_results: Dict[str, Any],
        refined_strategies: List[ProceduralKnowledge]
    ) -> Dict[str, Any]:
        """Add session experience to accumulated knowledge"""
        
        experience_record = {
            "session_id": session.session_id,
            "domain": session.domain,
            "duration": (session.end_time or datetime.now()) - session.start_time,
            "facts_learned_count": len(learning_results["facts_learned"]),
            "strategies_used": learning_results["strategies_used"],
            "success_rate": self._calculate_success_rate(learning_results),
            "performance_metrics": session.performance_metrics,
            "refined_strategies": [s.strategy_id for s in refined_strategies],
            "timestamp": datetime.now()
        }
        
        self.experience_database[session.session_id] = experience_record
        
        # Map cross-domain insights
        cross_domain_insights = await self.cross_domain_mapper.map_insights(
            session, learning_results
        )
        
        return {
            "experience_recorded": True,
            "cross_domain_insights": cross_domain_insights,
            "total_experiences": len(self.experience_database)
        }

## Veklom Integration

### 1. Agent Learning Enhancement
- Integrate MEMENTO with all agent types
- Enable continuous learning from web interactions
- Build domain expertise over time

### 2. Strategy Reuse System
- Share successful strategies across agents
- Build library of proven exploration patterns
- Enable cross-domain strategy transfer

### 3. Performance Improvement Tracking
- Monitor learning progress over time
- Measure expertise development
- Identify learning bottlenecks

## Success Metrics

| Metric | Target | MEMENTO-Inspired |
|---|---|---|
| Domain expertise improvement | +40% | Adaptive learning |
| Strategy reuse success | > 70% | Pattern recognition |
| Cross-session knowledge transfer | +60% | Experience accumulation |
| Research efficiency | +50% | Learned strategies |
| Task success rate improvement | +35% | Procedural learning |

## Dependencies

- Agent-063 (research lead)
- Agent-077 (planning scientist - for strategy optimization)
- All domain agents (for domain-specific learning)
- Web crawling infrastructure (for exploration)

---

## Research References

1. **MEMENTO**: Web as Learning Signal for Low-Data Domains (arXiv:2605.29795)
2. **PlanAhead**: Planning Representations for LLM Web Agents (arXiv:2605.29927)
3. **Ptah**: Verifiable Multimodal Deep Research (arXiv:2605.29861)
