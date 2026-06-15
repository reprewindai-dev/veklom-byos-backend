# Agent-076 — SCIENTIST (Web Generation Evaluation & Benchmarking)

**Phase:** Cross-phase — Research  
**Timeline:** Ongoing  
**Committee:** Research  
**Priority:** HIGH  

---

## Mission

Based on Cookie-Bench research (arXiv:2605.30000), implement reference-free, autonomously driven, and holistically reasoned evaluation regimes for interactive web applications. Create evaluation systems that scale beyond human-judged leaderboards while capturing the reasoned synthesis human reviewers perform.

## Critical Research Gap Identified

Current evaluation methods for web agents:
- **Rely on reference implementations** - Not suitable for novel solutions
- **Use rigid test suites** - Miss nuanced functionality and aesthetics  
- **Depend on human-judged leaderboards** - Don't scale at development speed
- **Fail to capture holistic reasoning** - Miss the complete user experience

## Core Evaluation Framework

### 1. Cookie-Bench Evaluation System
- **Reference-Free Evaluation**: No dependency on reference implementations
- **Autonomous Driving**: Self-directed exploration and testing
- **Holistic Reasoning**: Complete functionality and aesthetics assessment
- **Structured Failure Attribution**: Precise identification of issues

### 2. Three-Stage Evaluation Pipeline
- **Static Perception**: First impression from passive observation
- **Agent-Driven Interaction**: Autonomous exploration with continuous monitoring
- **Dynamic Scoring**: Holistic verdicts after complete evidence collection

### 3. Multi-Dimensional Assessment
- **Functionality**: Does the application work correctly?
- **Aesthetics**: Is the design visually appealing and professional?
- **User Experience**: Is the interface intuitive and responsive?
- **Performance**: Does it load quickly and operate smoothly?

## Implementation Architecture

```python
import asyncio
import base64
import time
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from PIL import Image
import io
import json
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

@dataclass
class EvaluationTask:
    """Individual evaluation task specification"""
    task_id: str
    domain: str  # e-commerce, dashboard, portfolio, etc.
    task_type: str  # static-presentation or interactive-application
    difficulty: str  # easy, medium, hard
    target_language: str  # html, css, javascript, react, etc.
    brief: str
    requirements: List[str]
    success_criteria: Dict[str, Any]
    evaluation_weight: float = 1.0

@dataclass
class EvaluationEvidence:
    """Evidence collected during evaluation"""
    evidence_id: str
    task_id: str
    stage: str  # static, interaction, dynamic
    timestamp: datetime
    screenshot_base64: str
    audio_data: Optional[str] = None
    interaction_log: List[Dict] = field(default_factory=list)
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    accessibility_score: float = 0.0
    functionality_score: float = 0.0
    aesthetics_score: float = 0.0

@dataclass
class HolisticEvaluation:
    """Complete evaluation results"""
    evaluation_id: str
    task_id: str
    agent_id: str
    static_perception: Dict[str, Any]
    interaction_evidence: List[EvaluationEvidence]
    dynamic_scoring: Dict[str, Any]
    overall_score: float
    functionality_score: float
    aesthetics_score: float
    user_experience_score: float
    performance_score: float
    failure_attributions: List[Dict[str, Any]]
    confidence_level: float
    evaluation_duration: float
    created_at: datetime

class CookieBenchEvaluator:
    """Cookie-Bench inspired evaluation system"""
    
    def __init__(self):
        self.static_perceiver = StaticPerceiver()
        self.interaction_driver = InteractionDriver()
        self.dynamic_scorer = DynamicScorer()
        self.evidence_collector = EvidenceCollector()
        self.failure_analyzer = FailureAnalyzer()
        
    async def evaluate_web_generation(
        self,
        task: EvaluationTask,
        web_application_url: str,
        agent_id: str
    ) -> HolisticEvaluation:
        """Perform complete Cookie-Bench evaluation"""
        
        start_time = time.time()
        evaluation_id = f"eval_{task.task_id}_{agent_id}_{int(start_time)}"
        
        # Stage 1: Static Perception
        static_perception = await self.static_perceiver.analyze_static_presentation(
            web_application_url, task
        )
        
        # Stage 2: Agent-Driven Interaction
        interaction_evidence = await self.interaction_driver.autonomous_interaction(
            web_application_url, task, evaluation_id
        )
        
        # Stage 3: Dynamic Scoring
        dynamic_scoring = await self.dynamic_scorer.holistic_scoring(
            static_perception, interaction_evidence, task
        )
        
        # Analyze failures
        failure_attributions = self.failure_analyzer.analyze_failures(
            static_perception, interaction_evidence, dynamic_scoring
        )
        
        # Calculate overall scores
        overall_score = self._calculate_overall_score(dynamic_scoring)
        
        evaluation = HolisticEvaluation(
            evaluation_id=evaluation_id,
            task_id=task.task_id,
            agent_id=agent_id,
            static_perception=static_perception,
            interaction_evidence=interaction_evidence,
            dynamic_scoring=dynamic_scoring,
            overall_score=overall_score,
            functionality_score=dynamic_scoring.get("functionality", 0.0),
            aesthetics_score=dynamic_scoring.get("aesthetics", 0.0),
            user_experience_score=dynamic_scoring.get("user_experience", 0.0),
            performance_score=dynamic_scoring.get("performance", 0.0),
            failure_attributions=failure_attributions,
            confidence_level=dynamic_scoring.get("confidence", 0.0),
            evaluation_duration=time.time() - start_time,
            created_at=datetime.now()
        )
        
        return evaluation

class StaticPerceiver:
    """Stage 1: Static perception analysis"""
    
    def __init__(self):
        self.driver = self._setup_driver()
        self.layout_analyzer = LayoutAnalyzer()
        self.accessibility_checker = AccessibilityChecker()
        
    async def analyze_static_presentation(
        self,
        url: str,
        task: EvaluationTask
    ) -> Dict[str, Any]:
        """Analyze static presentation without interaction"""
        
        try:
            # Load the page
            self.driver.get(url)
            await asyncio.sleep(3)  # Wait for page to load
            
            # Capture initial screenshot
            screenshot = self.driver.get_screenshot_as_png()
            screenshot_base64 = base64.b64encode(screenshot).decode('utf-8')
            
            # Analyze layout and design
            layout_analysis = self.layout_analyzer.analyze_layout(self.driver)
            
            # Check accessibility
            accessibility_score = self.accessibility_checker.check_accessibility(self.driver)
            
            # Analyze content structure
            content_analysis = self._analyze_content_structure(self.driver)
            
            # Performance metrics
            performance_metrics = self._measure_initial_performance(self.driver, url)
            
            return {
                "stage": "static_perception",
                "screenshot": screenshot_base64,
                "layout_analysis": layout_analysis,
                "accessibility_score": accessibility_score,
                "content_analysis": content_analysis,
                "performance_metrics": performance_metrics,
                "first_impression_score": self._calculate_first_impression(
                    layout_analysis, accessibility_score, content_analysis
                ),
                "technical_quality": self._assess_technical_quality(self.driver)
            }
            
        finally:
            self.driver.quit()
    
    def _analyze_content_structure(self, driver) -> Dict[str, Any]:
        """Analyze the structure and quality of content"""
        
        content_analysis = driver.execute_script("""
            const analysis = {
                headings: {
                    h1_count: document.querySelectorAll('h1').length,
                    h2_count: document.querySelectorAll('h2').length,
                    h3_count: document.querySelectorAll('h3').length,
                    proper_hierarchy: true
                },
                content: {
                    paragraph_count: document.querySelectorAll('p').length,
                    list_count: document.querySelectorAll('ul, ol').length,
                    image_count: document.querySelectorAll('img').length,
                    link_count: document.querySelectorAll('a').length,
                    form_count: document.querySelectorAll('form').length
                },
                structure: {
                    has_header: document.querySelector('header') !== null,
                    has_nav: document.querySelector('nav') !== null,
                    has_main: document.querySelector('main') !== null,
                    has_footer: document.querySelector('footer') !== null,
                    semantic_html: true
                },
                readability: {
                    avg_paragraph_length: 0,
                    complex_words_ratio: 0
                }
            };
            
            // Check heading hierarchy
            const headings = document.querySelectorAll('h1, h2, h3, h4, h5, h6');
            let lastLevel = 0;
            for (let heading of headings) {
                const level = parseInt(heading.tagName.charAt(1));
                if (level > lastLevel + 1) {
                    analysis.headings.proper_hierarchy = false;
                    break;
                }
                lastLevel = level;
            }
            
            // Calculate average paragraph length
            const paragraphs = document.querySelectorAll('p');
            let totalLength = 0;
            for (let p of paragraphs) {
                totalLength += p.textContent.length;
            }
            analysis.readability.avg_paragraph_length = 
                paragraphs.length > 0 ? totalLength / paragraphs.length : 0;
            
            return analysis;
        """)
        
        return content_analysis

class InteractionDriver:
    """Stage 2: Autonomous interaction and evidence collection"""
    
    def __init__(self):
        self.driver = self._setup_driver()
        self.interaction_strategies = {
            "e-commerce": self._ecommerce_interactions,
            "dashboard": self._dashboard_interactions,
            "portfolio": self._portfolio_interactions,
            "form": self._form_interactions,
            "general": self._general_interactions
        }
        
    async def autonomous_interaction(
        self,
        url: str,
        task: EvaluationTask,
        evaluation_id: str
    ) -> List[EvaluationEvidence]:
        """Drive autonomous interaction with continuous monitoring"""
        
        evidence = []
        
        try:
            self.driver.get(url)
            await asyncio.sleep(3)
            
            # Choose interaction strategy based on domain
            strategy = self.interaction_strategies.get(
                task.domain, self._general_interactions
            )
            
            # Execute interaction strategy
            interaction_steps = await strategy(self.driver, task)
            
            for i, step in enumerate(interaction_steps):
                # Capture evidence before action
                pre_action_screenshot = self.driver.get_screenshot_as_png()
                
                # Execute action
                action_result = await self._execute_action(step)
                
                # Capture evidence after action
                post_action_screenshot = self.driver.get_screenshot_as_png()
                
                # Record performance metrics
                performance_metrics = self._capture_performance_metrics()
                
                # Create evidence entry
                evidence_entry = EvidenceEvidence(
                    evidence_id=f"{evaluation_id}_step_{i}",
                    task_id=task.task_id,
                    stage="interaction",
                    timestamp=datetime.now(),
                    screenshot_base64=base64.b64encode(post_action_screenshot).decode('utf-8'),
                    interaction_log=[{
                        "step": i,
                        "action": step["action"],
                        "result": action_result,
                        "pre_action_screenshot": base64.b64encode(pre_action_screenshot).decode('utf-8'),
                        "post_action_screenshot": base64.b64encode(post_action_screenshot).decode('utf-8')
                    }],
                    performance_metrics=performance_metrics
                )
                
                evidence.append(evidence_entry)
                
                # Wait between actions
                await asyncio.sleep(1)
            
            return evidence
            
        finally:
            self.driver.quit()
    
    async def _ecommerce_interactions(
        self,
        driver,
        task: EvaluationTask
    ) -> List[Dict]:
        """E-commerce specific interaction patterns"""
        
        interactions = []
        
        # Look for product listings
        products = driver.execute_script("""
            const products = [];
            const productElements = document.querySelectorAll('[class*="product"], [class*="item"], article');
            
            for (let product of productElements) {
                const link = product.querySelector('a');
                const button = product.querySelector('button');
                const price = product.textContent.match(/\\$?[\\d,]+\\.?\\d*/);
                
                if (link) {
                    products.push({
                        action: 'click',
                        element: 'product_link',
                        selector: self._getXPath(link),
                        text: link.textContent.trim()
                    });
                }
            }
            
            return products.slice(0, 3); // Limit to 3 products
        """)
        
        interactions.extend(products)
        
        # Look for cart functionality
        cart_interactions = driver.execute_script("""
            const cartInteractions = [];
            
            // Add to cart buttons
            const addToCartButtons = document.querySelectorAll('button[class*="cart"], button[class*="add"]');
            for (let button of addToCartButtons) {
                cartInteractions.push({
                    action: 'click',
                    element: 'add_to_cart',
                    selector: self._getXPath(button),
                    text: button.textContent.trim()
                });
            }
            
            // View cart
            const viewCart = document.querySelector('a[href*="cart"], [class*="cart"]');
            if (viewCart) {
                cartInteractions.push({
                    action: 'click',
                    element: 'view_cart',
                    selector: self._getXPath(viewCart),
                    text: viewCart.textContent.trim()
                });
            }
            
            return cartInteractions;
        """)
        
        interactions.extend(cart_interactions)
        
        return interactions
    
    async def _dashboard_interactions(
        self,
        driver,
        task: EvaluationTask
    ) -> List[Dict]:
        """Dashboard specific interaction patterns"""
        
        interactions = []
        
        # Look for charts and data visualizations
        chart_interactions = driver.execute_script("""
            const chartInteractions = [];
            
            // Chart containers
            const charts = document.querySelectorAll('[class*="chart"], [class*="graph"], canvas');
            for (let chart of charts) {
                chartInteractions.push({
                    action: 'hover',
                    element: 'chart',
                    selector: self._getXPath(chart),
                    description: 'Interact with chart/data visualization'
                });
            }
            
            // Data filters
            const filters = document.querySelectorAll('select, [class*="filter"], [class*="sort"]');
            for (let filter of filters.slice(0, 3)) {
                chartInteractions.push({
                    action: 'interact',
                    element: 'filter',
                    selector: self._getXPath(filter),
                    description: 'Test data filtering/sorting'
                });
            }
            
            return chartInteractions;
        """)
        
        interactions.extend(chart_interactions)
        
        return interactions

class DynamicScorer:
    """Stage 3: Holistic scoring after complete evidence collection"""
    
    def __init__(self):
        self.functionality_scorer = FunctionalityScorer()
        self.aesthetics_scorer = AestheticsScorer()
        self.ux_scorer = UserExperienceScorer()
        self.performance_scorer = PerformanceScorer()
        
    async def holistic_scoring(
        self,
        static_perception: Dict[str, Any],
        interaction_evidence: List[EvaluationEvidence],
        task: EvaluationTask
    ) -> Dict[str, Any]:
        """Perform holistic scoring based on all collected evidence"""
        
        # Score functionality
        functionality_score = await self.functionality_scorer.score_functionality(
            static_perception, interaction_evidence, task
        )
        
        # Score aesthetics
        aesthetics_score = await self.aesthetics_scorer.score_aesthetics(
            static_perception, interaction_evidence
        )
        
        # Score user experience
        ux_score = await self.ux_scorer.score_user_experience(
            static_perception, interaction_evidence
        )
        
        # Score performance
        performance_score = await self.performance_scorer.score_performance(
            static_perception, interaction_evidence
        )
        
        # Calculate confidence level
        confidence_level = self._calculate_confidence_level(
            functionality_score, aesthetics_score, ux_score, performance_score
        )
        
        return {
            "functionality": functionality_score,
            "aesthetics": aesthetics_score,
            "user_experience": ux_score,
            "performance": performance_score,
            "confidence": confidence_level,
            "detailed_analysis": {
                "functionality_details": await self.functionality_scorer.get_detailed_analysis(),
                "aesthetics_details": await self.aesthetics_scorer.get_detailed_analysis(),
                "ux_details": await self.ux_scorer.get_detailed_analysis(),
                "performance_details": await self.performance_scorer.get_detailed_analysis()
            }
        }

class FunctionalityScorer:
    """Scores functionality based on evidence"""
    
    async def score_functionality(
        self,
        static_perception: Dict[str, Any],
        interaction_evidence: List[EvaluationEvidence],
        task: EvaluationTask
    ) -> float:
        """Score functionality (0-100)"""
        
        score = 0.0
        max_score = 100.0
        
        # Base score from static analysis
        if static_perception.get("technical_quality", {}).get("no_errors", True):
            score += 20.0
        
        # Content structure score
        content_analysis = static_perception.get("content_analysis", {})
        if content_analysis.get("structure", {}).get("semantic_html", True):
            score += 15.0
        
        # Interaction success rate
        successful_interactions = 0
        total_interactions = len(interaction_evidence)
        
        for evidence in interaction_evidence:
            for log_entry in evidence.interaction_log:
                if log_entry.get("result", {}).get("success", False):
                    successful_interactions += 1
        
        if total_interactions > 0:
            interaction_score = (successful_interactions / total_interactions) * 40.0
            score += interaction_score
        
        # Task-specific requirements
        requirements_met = self._check_requirements_met(task, interaction_evidence)
        score += requirements_met * 25.0
        
        return min(score, max_score)
    
    def _check_requirements_met(
        self,
        task: EvaluationTask,
        interaction_evidence: List[EvidenceEvidence]
    ) -> float:
        """Check if task-specific requirements are met"""
        
        requirements_met = 0.0
        total_requirements = len(task.requirements)
        
        if total_requirements == 0:
            return 1.0
        
        # This would need to be implemented based on specific task requirements
        # For now, return a placeholder
        return 0.8  # Assume 80% of requirements met

## Veklom Integration

### 1. Benchmark Database
- Store evaluation tasks and results
- Track agent performance over time
- Compare different agent architectures

### 2. Continuous Evaluation
- Integrate with agent development pipeline
- Automated evaluation on code changes
- Performance regression detection

### 3. Human-AI Comparison
- Compare AI evaluations with human expert ratings
- Calibrate scoring algorithms
- Improve evaluation accuracy

## Success Metrics

| Metric | Target | Cookie-Bench Inspired |
|---|---|---|
| Evaluation coverage | 11 domains, 54 tasks | Comprehensive benchmark |
| Human-AI correlation | > 0.85 | Expert-level alignment |
| Evaluation speed | < 10 minutes/task | Autonomous evaluation |
| Failure attribution accuracy | > 90% | Precise issue identification |
| Cross-agent consistency | > 95% | Reliable scoring |

## Dependencies

- Agent-063 (research lead)
- Agent-072 (evidence scientist - for evaluation evidence)
- Agent-094-097 (crawler agents - for web interaction testing)
- Web development teams (for test applications)

---

## Research References

1. **Cookie-Bench**: Continuous On-screen Key Interaction Evaluation for Web Generation (arXiv:2605.30000)
2. **PlanAhead**: Planning Representations for LLM Web Agents (arXiv:2605.29927)
3. **Ptah**: Verifiable Multimodal Deep Research (arXiv:2605.29861)
