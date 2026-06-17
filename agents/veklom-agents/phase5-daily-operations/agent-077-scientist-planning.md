# Agent-077 — SCIENTIST (Planning Representation Optimization)

**Phase:** Cross-phase — Research  
**Timeline:** Ongoing  
**Committee:** Research  
**Priority:** HIGH  

---

## Mission

Based on PlanAhead research (arXiv:2605.29927), optimize planning representations for LLM-based web agents. Systematically evaluate different plan formats to improve agent robustness, task success rates, and consistency across different multimodal LLM families.

## Critical Research Finding

**Plan representation significantly influences web-agent performance**:
- Sequential subgoals, narrative, pseudocode, and checklist formats
- Different LLM families respond differently to plan representations
- Novel evaluation metrics needed: Achievement Rate (AR) and Solved-Task Consistency (STC)

## Core Research Areas

### 1. Plan Representation Analysis
- **Sequential Subgoals**: Step-by-step breakdown with clear dependencies
- **Narrative Plans**: Story-like descriptions of the task flow
- **Pseudocode Plans**: Code-like structured planning format
- **Checklist Plans**: Itemized task completion tracking

### 2. Difficulty Categorization
- **Automatic Task Classification**: Categorize tasks by difficulty without human annotation
- **Consistent Difficulty Grading**: Ensure comparable evaluation across plan types
- **Performance Benchmarking**: Establish baseline performance metrics

### 3. Cross-LLM Evaluation
- **Family-Specific Optimization**: Tailor plans for different LLM architectures
- **Robustness Testing**: Evaluate performance across model families
- **Consistency Measurement**: Track performance stability

## Implementation Architecture

```python
import json
import time
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import numpy as np
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer

class PlanRepresentation(Enum):
    """Different plan representation types"""
    SEQUENTIAL_SUBGOALS = "sequential_subgoals"
    NARRATIVE = "narrative"
    PSEUDOCODE = "pseudocode"
    CHECKLIST = "checklist"

class DifficultyLevel(Enum):
    """Task difficulty levels"""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"

@dataclass
class TaskSpecification:
    """Web agent task specification"""
    task_id: str
    description: str
    domain: str
    objective: str
    success_criteria: List[str]
    constraints: List[str]
    difficulty_level: DifficultyLevel
    estimated_steps: int
    required_tools: List[str]

@dataclass
class PlanTemplate:
    """Template for different plan representations"""
    representation_type: PlanRepresentation
    template_structure: Dict[str, Any]
    formatting_rules: Dict[str, str]
    example_usage: str
    best_for_llm_families: List[str]

@dataclass
class PlanExecutionResult:
    """Result of plan execution"""
    plan_id: str
    task_id: str
    representation_type: PlanRepresentation
    llm_family: str
    execution_steps: List[Dict[str, Any]]
    success: bool
    achievement_rate: float
    execution_time: float
    errors_encountered: List[str]
    deviations_from_plan: List[str]

class PlanAheadOptimizer:
    """PlanAhead-inspired planning optimization system"""
    
    def __init__(self):
        self.task_classifier = TaskDifficultyClassifier()
        self.plan_generator = PlanGenerator()
        self.execution_evaluator = PlanExecutionEvaluator()
        self.performance_analyzer = PerformanceAnalyzer()
        self.llm_adapter = LLMFamilyAdapter()
        
    def optimize_planning_representation(
        self,
        task: TaskSpecification,
        available_llms: List[str]
    ) -> Dict[str, Any]:
        """Optimize planning representation for specific task and LLMs"""
        
        # Step 1: Classify task difficulty (if not already classified)
        if task.difficulty_level == DifficultyLevel.HARD:
            difficulty_analysis = self.task_classifier.analyze_difficulty(task)
            task.difficulty_level = difficulty_analysis["predicted_difficulty"]
        
        # Step 2: Generate different plan representations
        plan_representations = {}
        for representation_type in PlanRepresentation:
            plan = self.plan_generator.generate_plan(
                task, representation_type
            )
            plan_representations[representation_type] = plan
        
        # Step 3: Test plans across different LLM families
        execution_results = {}
        for llm_family in available_llms:
            llm_results = {}
            for representation_type, plan in plan_representations.items():
                # Adapt plan for specific LLM family
                adapted_plan = self.llm_adapter.adapt_plan(
                    plan, representation_type, llm_family
                )
                
                # Execute plan
                result = self.execution_evaluator.execute_plan(
                    task, adapted_plan, llm_family
                )
                llm_results[representation_type] = result
            
            execution_results[llm_family] = llm_results
        
        # Step 4: Analyze performance and recommend optimal representation
        performance_analysis = self.performance_analyzer.analyze_performance(
            execution_results, task
        )
        
        # Step 5: Generate optimization recommendations
        recommendations = self._generate_recommendations(
            performance_analysis, task, available_llms
        )
        
        return {
            "task": task,
            "plan_representations": plan_representations,
            "execution_results": execution_results,
            "performance_analysis": performance_analysis,
            "recommendations": recommendations,
            "optimization_timestamp": datetime.now().isoformat()
        }

class TaskDifficultyClassifier:
    """Automatically classifies task difficulty without human annotation"""
    
    def __init__(self):
        self.vectorizer = TfidfVectorizer(max_features=1000)
        self.difficulty_features = {
            "complexity_indicators": [
                "multiple_steps", "conditional_logic", "data_extraction",
                "form_filling", "navigation_complexity", "error_handling"
            ],
            "domain_complexity": {
                "e-commerce": 0.6,
                "social_media": 0.4,
                "productivity": 0.7,
                "development": 0.9,
                "research": 0.8
            }
        }
        
    def analyze_difficulty(self, task: TaskSpecification) -> Dict[str, Any]:
        """Analyze and predict task difficulty"""
        
        # Extract features from task description
        complexity_score = self._calculate_complexity_score(task)
        domain_score = self.difficulty_features["domain_complexity"].get(
            task.domain, 0.5
        )
        
        # Calculate steps complexity
        steps_complexity = min(1.0, task.estimated_steps / 20.0)
        
        # Tool requirements complexity
        tools_complexity = min(1.0, len(task.required_tools) / 10.0)
        
        # Constraint complexity
        constraints_complexity = min(1.0, len(task.constraints) / 5.0)
        
        # Combine scores
        overall_difficulty = (
            complexity_score * 0.3 +
            domain_score * 0.2 +
            steps_complexity * 0.2 +
            tools_complexity * 0.15 +
            constraints_complexity * 0.15
        )
        
        # Classify difficulty
        if overall_difficulty < 0.4:
            predicted_difficulty = DifficultyLevel.EASY
        elif overall_difficulty < 0.7:
            predicted_difficulty = DifficultyLevel.MEDIUM
        else:
            predicted_difficulty = DifficultyLevel.HARD
        
        return {
            "predicted_difficulty": predicted_difficulty,
            "overall_score": overall_difficulty,
            "complexity_score": complexity_score,
            "domain_score": domain_score,
            "steps_complexity": steps_complexity,
            "tools_complexity": tools_complexity,
            "constraints_complexity": constraints_complexity,
            "confidence": 0.85
        }
    
    def _calculate_complexity_score(self, task: TaskSpecification) -> float:
        """Calculate complexity score from task description"""
        
        complexity_keywords = {
            "high": ["if", "else", "conditional", "verify", "validate", "compare"],
            "medium": ["navigate", "click", "fill", "submit", "extract"],
            "low": ["open", "view", "read", "simple", "basic"]
        }
        
        description = task.description.lower()
        objective = task.objective.lower()
        
        high_complexity_count = sum(
            1 for keyword in complexity_keywords["high"]
            if keyword in description or keyword in objective
        )
        
        medium_complexity_count = sum(
            1 for keyword in complexity_keywords["medium"]
            if keyword in description or keyword in objective
        )
        
        # Weight the counts
        complexity_score = (
            high_complexity_count * 0.3 +
            medium_complexity_count * 0.15
        )
        
        return min(1.0, complexity_score)

class PlanGenerator:
    """Generates plans in different representations"""
    
    def __init__(self):
        self.plan_templates = self._initialize_plan_templates()
        
    def generate_plan(
        self,
        task: TaskSpecification,
        representation_type: PlanRepresentation
    ) -> Dict[str, Any]:
        """Generate plan in specified representation format"""
        
        if representation_type == PlanRepresentation.SEQUENTIAL_SUBGOALS:
            return self._generate_sequential_subgoals_plan(task)
        elif representation_type == PlanRepresentation.NARRATIVE:
            return self._generate_narrative_plan(task)
        elif representation_type == PlanRepresentation.PSEUDOCODE:
            return self._generate_pseudocode_plan(task)
        elif representation_type == PlanRepresentation.CHECKLIST:
            return self._generate_checklist_plan(task)
        else:
            raise ValueError(f"Unsupported representation type: {representation_type}")
    
    def _generate_sequential_subgoals_plan(self, task: TaskSpecification) -> Dict[str, Any]:
        """Generate sequential subgoals plan"""
        
        plan = {
            "representation_type": PlanRepresentation.SEQUENTIAL_SUBGOALS,
            "task_id": task.task_id,
            "objective": task.objective,
            "subgoals": []
        }
        
        # Break down task into sequential subgoals
        subgoals = self._decompose_into_subgoals(task)
        
        for i, subgoal in enumerate(subgoals):
            plan["subgoals"].append({
                "subgoal_id": f"subgoal_{i+1}",
                "description": subgoal["description"],
                "prerequisites": subgoal.get("prerequisites", []),
                "expected_outcome": subgoal.get("outcome", ""),
                "validation_criteria": subgoal.get("validation", []),
                "estimated_time": subgoal.get("time", 60)
            })
        
        return plan
    
    def _generate_narrative_plan(self, task: TaskSpecification) -> Dict[str, Any]:
        """Generate narrative-style plan"""
        
        plan = {
            "representation_type": PlanRepresentation.NARRATIVE,
            "task_id": task.task_id,
            "story": self._create_task_narrative(task),
            "scenes": []
        }
        
        # Create narrative scenes
        scenes = self._create_narrative_scenes(task)
        
        for i, scene in enumerate(scenes):
            plan["scenes"].append({
                "scene_id": f"scene_{i+1}",
                "title": scene["title"],
                "description": scene["description"],
                "actions": scene["actions"],
                "transition": scene.get("transition", ""),
                "success_indicators": scene.get("indicators", [])
            })
        
        return plan
    
    def _generate_pseudocode_plan(self, task: TaskSpecification) -> Dict[str, Any]:
        """Generate pseudocode-style plan"""
        
        plan = {
            "representation_type": PlanRepresentation.PSEUDOCODE,
            "task_id": task.task_id,
            "algorithm": self._create_algorithm_structure(task),
            "functions": []
        }
        
        # Create function-like structures
        functions = self._decompose_into_functions(task)
        
        for func in functions:
            plan["functions"].append({
                "function_name": func["name"],
                "parameters": func.get("parameters", []),
                "steps": func["steps"],
                "return_value": func.get("return", ""),
                "error_handling": func.get("error_handling", [])
            })
        
        return plan
    
    def _generate_checklist_plan(self, task: TaskSpecification) -> Dict[str, Any]:
        """Generate checklist-style plan"""
        
        plan = {
            "representation_type": PlanRepresentation.CHECKLIST,
            "task_id": task.task_id,
            "checklist": []
        }
        
        # Create checklist items
        checklist_items = self._create_checklist_items(task)
        
        for i, item in enumerate(checklist_items):
            plan["checklist"].append({
                "item_id": f"item_{i+1}",
                "description": item["description"],
                "category": item.get("category", "general"),
                "priority": item.get("priority", "medium"),
                "verification_method": item.get("verification", "manual"),
                "dependencies": item.get("dependencies", []),
                "completed": False
            })
        
        return plan

class PlanExecutionEvaluator:
    """Evaluates plan execution with AR and STC metrics"""
    
    def __init__(self):
        self.execution_tracker = ExecutionTracker()
        self.metric_calculator = MetricCalculator()
        
    def execute_plan(
        self,
        task: TaskSpecification,
        plan: Dict[str, Any],
        llm_family: str
    ) -> PlanExecutionResult:
        """Execute plan and evaluate performance"""
        
        plan_id = f"plan_{task.task_id}_{plan['representation_type']}_{int(time.time())}"
        
        # Track execution
        execution_steps = []
        start_time = time.time()
        
        try:
            # Execute plan based on representation type
            if plan["representation_type"] == PlanRepresentation.SEQUENTIAL_SUBGOALS:
                execution_result = self._execute_sequential_subgoals(
                    task, plan, llm_family
                )
            elif plan["representation_type"] == PlanRepresentation.NARRATIVE:
                execution_result = self._execute_narrative_plan(
                    task, plan, llm_family
                )
            elif plan["representation_type"] == PlanRepresentation.PSEUDOCODE:
                execution_result = self._execute_pseudocode_plan(
                    task, plan, llm_family
                )
            elif plan["representation_type"] == PlanRepresentation.CHECKLIST:
                execution_result = self._execute_checklist_plan(
                    task, plan, llm_family
                )
            
            execution_steps = execution_result["steps"]
            success = execution_result["success"]
            errors = execution_result["errors"]
            deviations = execution_result["deviations"]
            
        except Exception as e:
            success = False
            errors = [f"Execution failed: {str(e)}"]
            deviations = []
        
        execution_time = time.time() - start_time
        
        # Calculate Achievement Rate (AR)
        achievement_rate = self.metric_calculator.calculate_achievement_rate(
            task, execution_steps, success
        )
        
        return PlanExecutionResult(
            plan_id=plan_id,
            task_id=task.task_id,
            representation_type=plan["representation_type"],
            llm_family=llm_family,
            execution_steps=execution_steps,
            success=success,
            achievement_rate=achievement_rate,
            execution_time=execution_time,
            errors_encountered=errors,
            deviations_from_plan=deviations
        )

class MetricCalculator:
    """Calculates AR and STC metrics"""
    
    def calculate_achievement_rate(
        self,
        task: TaskSpecification,
        execution_steps: List[Dict[str, Any]],
        success: bool
    ) -> float:
        """Calculate Achievement Rate (AR) metric"""
        
        if not execution_steps:
            return 0.0
        
        # Count successful steps
        successful_steps = sum(
            1 for step in execution_steps
            if step.get("success", False)
        )
        
        # Weight by criticality
        weighted_success = 0.0
        total_weight = 0.0
        
        for step in execution_steps:
            weight = step.get("criticality", 1.0)
            total_weight += weight
            
            if step.get("success", False):
                weighted_success += weight
        
        # Calculate AR
        if total_weight > 0:
            ar = (weighted_success / total_weight) * 100
        else:
            ar = 0.0
        
        # Bonus for overall success
        if success:
            ar = min(100.0, ar + 10.0)
        
        return ar
    
    def calculate_solved_task_consistency(
        self,
        multiple_executions: List[PlanExecutionResult]
    ) -> float:
        """Calculate Solved-Task Consistency (STC) metric"""
        
        if not multiple_executions:
            return 0.0
        
        # Count successful executions
        successful_executions = sum(
            1 for result in multiple_executions
            if result.success
        )
        
        # Calculate consistency
        stc = (successful_executions / len(multiple_executions)) * 100
        
        return stc

class PerformanceAnalyzer:
    """Analyzes performance across different plan representations and LLMs"""
    
    def analyze_performance(
        self,
        execution_results: Dict[str, Dict[PlanRepresentation, PlanExecutionResult]],
        task: TaskSpecification
    ) -> Dict[str, Any]:
        """Analyze performance and identify optimal configurations"""
        
        analysis = {
            "overall_performance": {},
            "llm_family_performance": {},
            "representation_performance": {},
            "optimal_configurations": {},
            "performance_insights": []
        }
        
        # Analyze overall performance
        all_results = []
        for llm_family, llm_results in execution_results.items():
            for representation, result in llm_results.items():
                all_results.append(result)
        
        if all_results:
            analysis["overall_performance"] = {
                "average_achievement_rate": np.mean([r.achievement_rate for r in all_results]),
                "average_success_rate": np.mean([1 if r.success else 0 for r in all_results]) * 100,
                "average_execution_time": np.mean([r.execution_time for r in all_results]),
                "total_executions": len(all_results)
            }
        
        # Analyze performance by LLM family
        for llm_family, llm_results in execution_results.items():
            llm_results_list = list(llm_results.values())
            
            analysis["llm_family_performance"][llm_family] = {
                "average_achievement_rate": np.mean([r.achievement_rate for r in llm_results_list]),
                "success_rate": np.mean([1 if r.success else 0 for r in llm_results_list]) * 100,
                "best_representation": max(
                    llm_results.items(),
                    key=lambda x: x[1].achievement_rate
                )[0].value,
                "consistency": self._calculate_consistency(llm_results_list)
            }
        
        # Analyze performance by representation
        representation_results = {}
        for llm_results in execution_results.values():
            for representation, result in llm_results.items():
                if representation not in representation_results:
                    representation_results[representation] = []
                representation_results[representation].append(result)
        
        for representation, results in representation_results.items():
            analysis["representation_performance"][representation.value] = {
                "average_achievement_rate": np.mean([r.achievement_rate for r in results]),
                "success_rate": np.mean([1 if r.success else 0 for r in results]) * 100,
                "best_llm_family": max(
                    zip(execution_results.keys(), [r for r in results if r in execution_results.values()]),
                    key=lambda x: x[1].achievement_rate
                )[0] if execution_results else "unknown",
                "cross_llm_consistency": self._calculate_consistency(results)
            }
        
        # Identify optimal configurations
        analysis["optimal_configurations"] = self._identify_optimal_configurations(
            execution_results
        )
        
        return analysis
    
    def _calculate_consistency(self, results: List[PlanExecutionResult]) -> float:
        """Calculate consistency score for a set of results"""
        
        if len(results) < 2:
            return 100.0
        
        achievement_rates = [r.achievement_rate for r in results]
        consistency = 100.0 - (np.std(achievement_rates) / np.mean(achievement_rates) * 100)
        
        return max(0.0, consistency)

## Veklom Integration

### 1. Agent Planning Enhancement
- Integrate with existing agent planning systems
- Auto-select optimal plan representations
- Monitor planning performance over time

### 2. Cross-Agent Optimization
- Share planning insights across agent types
- Build planning best practices library
- Continuous learning from execution results

### 3. Performance Monitoring
- Track AR and STC metrics across all agents
- Identify planning bottlenecks
- Optimize resource allocation

## Success Metrics

| Metric | Target | PlanAhead Inspired |
|---|---|---|
| Achievement Rate (AR) | > 85% | Optimized planning |
| Solved-Task Consistency (STC) | > 90% | Reliable performance |
| Cross-LLM robustness | > 80% | Family-agnostic planning |
| Planning efficiency | +40% | Reduced planning overhead |
| Error reduction | -50% | Better plan representations |

## Dependencies

- Agent-063 (research lead)
- Agent-076 (evaluation scientist - for plan testing)
- All agent types (for planning optimization)
- LLM integration teams (for family-specific adaptations)

---

## Research References

1. **PlanAhead**: Planning Representations for LLM Web Agents (arXiv:2605.29927)
2. **Cookie-Bench**: Continuous On-screen Key Interaction Evaluation (arXiv:2605.30000)
3. **WebChallenger**: Reliable and Efficient Generalist Web Agent (arXiv:2606.10423)
