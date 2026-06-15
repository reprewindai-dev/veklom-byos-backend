# Agent-075 — SCIENTIST (Evidence-Based Research Optimization)

**Phase:** Cross-phase — Research  
**Timeline:** Ongoing  
**Committee:** Research  
**Priority:** HIGH  

---

## Mission

Based on "AI Scientists Are Only as Good as Their Evidence" (arXiv:2606.09556), optimize the evidence substrate for knowledge-intensive scientific decisions. Research and implement evidence generation, validation, and synthesis systems that become the primary limiting factor for scientific agent performance.

## Critical Research Finding

For knowledge-intensive scientific decisions, the **evidence substrate** is the limiting factor, not:
- Model capability
- Prompting techniques  
- Reasoning scaffolds

This fundamentally changes how we should approach scientific agent development.

## Core Research Areas

### 1. Evidence Substrate Optimization
- **Evidence Quality Metrics**: Define and measure evidence quality
- **Evidence Synthesis**: Combine multiple evidence sources effectively
- **Evidence Validation**: Ensure evidence reliability and accuracy
- **Evidence Retrieval**: Optimize evidence access and retrieval systems

### 2. Stratified Evidence Analysis
- **Domain-Specific Evidence**: Tailor evidence systems to specific domains
- **Evidence Hierarchies**: Create evidence hierarchies for different decision types
- **Evidence Integration**: Combine proprietary and public evidence sources
- **Evidence Freshness**: Maintain up-to-date evidence bases

### 3. Evidence-Driven Decision Making
- **Evidence-Weighted Reasoning**: Weight decisions by evidence quality
- **Evidence Gap Identification**: Identify and fill evidence gaps
- **Evidence-Based Hypothesis Testing**: Use evidence to drive scientific inquiry
- **Evidence Communication**: Effectively communicate evidence-based findings

## Implementation Architecture

```python
import numpy as np
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import json
import hashlib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import networkx as nx

@dataclass
class EvidenceItem:
    """Individual evidence item with quality metrics"""
    evidence_id: str
    content: str
    source: str
    source_type: str  # proprietary, public, experimental, theoretical
    domain: str
    confidence_score: float
    reliability_score: float
    freshness_score: float
    relevance_score: float
    metadata: Dict[str, Any]
    created_at: datetime
    verified_at: Optional[datetime] = None
    verification_status: str = "pending"
    citations: List[str] = field(default_factory=list)
    contradictions: List[str] = field(default_factory=list)

@dataclass
class EvidenceSynthesis:
    """Synthesized evidence from multiple sources"""
    synthesis_id: str
    research_question: str
    evidence_items: List[str]
    synthesis_method: str
    confidence_level: float
    consensus_level: float
    gaps_identified: List[str]
    contradictions_resolved: List[str]
    new_insights: List[str]
    created_at: datetime

@dataclass
class EvidenceBasedDecision:
    """Decision made based on evidence analysis"""
    decision_id: str
    research_context: str
    evidence_basis: List[str]
    reasoning_chain: List[str]
    confidence_level: float
    uncertainty_sources: List[str]
    alternative_hypotheses: List[str]
    decision_outcome: str
    validation_required: bool
    created_at: datetime

class EvidenceSubstrateOptimizer:
    """Optimizes evidence substrate for scientific decision making"""
    
    def __init__(self):
        self.evidence_store = EvidenceStore()
        self.quality_assessor = EvidenceQualityAssessor()
        self.synthesizer = EvidenceSynthesizer()
        self.validator = EvidenceValidator()
        self.retriever = EvidenceRetriever()
        self.gap_detector = EvidenceGapDetector()
        
    def optimize_evidence_substrate(
        self,
        research_domain: str,
        decision_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Optimize evidence substrate for specific research context"""
        
        # Step 1: Assess current evidence quality
        quality_assessment = self.quality_assessor.assess_domain_evidence(
            research_domain, decision_context
        )
        
        # Step 2: Identify evidence gaps
        evidence_gaps = self.gap_detector.identify_gaps(
            research_domain, decision_context, quality_assessment
        )
        
        # Step 3: Synthesize existing evidence
        evidence_synthesis = self.synthesizer.synthesize_domain_evidence(
            research_domain, quality_assessment
        )
        
        # Step 4: Validate evidence quality
        validation_results = self.validator.validate_evidence_synthesis(
            evidence_synthesis
        )
        
        # Step 5: Generate optimization recommendations
        optimization_plan = self._generate_optimization_plan(
            quality_assessment, evidence_gaps, evidence_synthesis, validation_results
        )
        
        return {
            "domain": research_domain,
            "context": decision_context,
            "quality_assessment": quality_assessment,
            "evidence_gaps": evidence_gaps,
            "synthesis": evidence_synthesis,
            "validation": validation_results,
            "optimization_plan": optimization_plan
        }

class EvidenceQualityAssessor:
    """Assesses quality of evidence items"""
    
    def __init__(self):
        self.quality_dimensions = {
            "reliability": 0.3,
            "freshness": 0.2,
            "relevance": 0.25,
            "confidence": 0.25
        }
        
    def assess_domain_evidence(
        self,
        domain: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Assess quality of evidence in a domain"""
        
        # Get all evidence for domain
        evidence_items = self._get_domain_evidence(domain)
        
        # Assess individual evidence quality
        quality_scores = []
        for evidence in evidence_items:
            quality_score = self._assess_evidence_quality(evidence, context)
            quality_scores.append(quality_score)
        
        # Calculate aggregate quality metrics
        aggregate_quality = self._calculate_aggregate_quality(quality_scores)
        
        # Identify quality issues
        quality_issues = self._identify_quality_issues(evidence_items, quality_scores)
        
        return {
            "domain": domain,
            "total_evidence_items": len(evidence_items),
            "average_quality_score": np.mean(quality_scores),
            "quality_distribution": self._get_quality_distribution(quality_scores),
            "quality_issues": quality_issues,
            "high_quality_evidence": len([q for q in quality_scores if q > 0.8]),
            "low_quality_evidence": len([q for q in quality_scores if q < 0.5]),
            "assessment_timestamp": datetime.now().isoformat()
        }
    
    def _assess_evidence_quality(
        self,
        evidence: EvidenceItem,
        context: Dict[str, Any]
    ) -> float:
        """Assess quality of individual evidence item"""
        
        # Base quality scores
        reliability_weight = self.quality_dimensions["reliability"]
        freshness_weight = self.quality_dimensions["freshness"]
        relevance_weight = self.quality_dimensions["relevance"]
        confidence_weight = self.quality_dimensions["confidence"]
        
        # Calculate weighted quality score
        quality_score = (
            evidence.reliability_score * reliability_weight +
            evidence.freshness_score * freshness_weight +
            evidence.relevance_score * relevance_weight +
            evidence.confidence_score * confidence_weight
        )
        
        # Apply context-specific adjustments
        context_adjustment = self._calculate_context_adjustment(evidence, context)
        
        return min(1.0, quality_score + context_adjustment)
    
    def _calculate_context_adjustment(
        self,
        evidence: EvidenceItem,
        context: Dict[str, Any]
    ) -> float:
        """Calculate context-specific quality adjustments"""
        
        adjustment = 0.0
        
        # Source type adjustments
        if evidence.source_type == "proprietary":
            adjustment += 0.1  # Proprietary sources often more reliable
        elif evidence.source_type == "experimental":
            adjustment -= 0.05  # Experimental evidence less reliable
        
        # Domain relevance adjustments
        if evidence.domain == context.get("target_domain"):
            adjustment += 0.05  # Direct domain relevance
        
        # Freshness adjustments for time-sensitive domains
        if context.get("time_sensitive", False):
            days_old = (datetime.now() - evidence.created_at).days
            if days_old > 365:
                adjustment -= 0.1  # Old evidence less relevant
        
        return adjustment

class EvidenceSynthesizer:
    """Synthesizes evidence from multiple sources"""
    
    def __init__(self):
        self.synthesis_methods = [
            "meta_analysis",
            "systematic_review",
            "consensus_building",
            "pattern_identification",
            "contradiction_resolution"
        ]
        
    def synthesize_domain_evidence(
        self,
        domain: str,
        quality_assessment: Dict[str, Any]
    ) -> EvidenceSynthesis:
        """Synthesize evidence for a domain"""
        
        # Get high-quality evidence
        high_quality_evidence = self._get_high_quality_evidence(
            domain, quality_assessment
        )
        
        # Choose synthesis method based on evidence characteristics
        synthesis_method = self._choose_synthesis_method(high_quality_evidence)
        
        # Perform synthesis
        synthesis_result = self._perform_synthesis(
            high_quality_evidence, synthesis_method
        )
        
        # Identify gaps and contradictions
        gaps = self._identify_evidence_gaps(high_quality_evidence)
        contradictions = self._identify_contradictions(high_quality_evidence)
        
        # Generate new insights
        insights = self._generate_new_insights(synthesis_result, gaps, contradictions)
        
        synthesis = EvidenceSynthesis(
            synthesis_id=f"synthesis_{domain}_{int(datetime.now().timestamp())}",
            research_question=f"What is the current understanding of {domain}?",
            evidence_items=[e.evidence_id for e in high_quality_evidence],
            synthesis_method=synthesis_method,
            confidence_level=synthesis_result["confidence"],
            consensus_level=synthesis_result["consensus"],
            gaps_identified=gaps,
            contradictions_resolved=contradictions,
            new_insights=insights,
            created_at=datetime.now()
        )
        
        return synthesis
    
    def _perform_synthesis(
        self,
        evidence_items: List[EvidenceItem],
        method: str
    ) -> Dict[str, Any]:
        """Perform evidence synthesis using specified method"""
        
        if method == "meta_analysis":
            return self._meta_analysis_synthesis(evidence_items)
        elif method == "systematic_review":
            return self._systematic_review_synthesis(evidence_items)
        elif method == "consensus_building":
            return self._consensus_building_synthesis(evidence_items)
        elif method == "pattern_identification":
            return self._pattern_identification_synthesis(evidence_items)
        elif method == "contradiction_resolution":
            return self._contradiction_resolution_synthesis(evidence_items)
        else:
            return self._default_synthesis(evidence_items)
    
    def _meta_analysis_synthesis(
        self,
        evidence_items: List[EvidenceItem]
    ) -> Dict[str, Any]:
        """Perform meta-analysis synthesis"""
        
        # Extract quantitative data from evidence
        quantitative_data = []
        for evidence in evidence_items:
            if "quantitative_results" in evidence.metadata:
                quantitative_data.append(evidence.metadata["quantitative_results"])
        
        if not quantitative_data:
            return {"confidence": 0.5, "consensus": 0.3, "method": "meta_analysis"}
        
        # Calculate effect sizes and confidence intervals
        effect_sizes = [data.get("effect_size", 0) for data in quantitative_data]
        confidence_intervals = [data.get("confidence_interval", [0, 0]) for data in quantitative_data]
        
        # Aggregate results
        mean_effect_size = np.mean(effect_sizes)
        effect_size_std = np.std(effect_sizes)
        
        # Calculate confidence and consensus
        confidence = 1.0 - (effect_size_std / abs(mean_effect_size) if mean_effect_size != 0 else 1.0)
        consensus = 1.0 - (np.std([ci[1] - ci[0] for ci in confidence_intervals]) / np.mean([ci[1] - ci[0] for ci in confidence_intervals]))
        
        return {
            "confidence": min(1.0, max(0.0, confidence)),
            "consensus": min(1.0, max(0.0, consensus)),
            "mean_effect_size": mean_effect_size,
            "effect_size_std": effect_size_std,
            "method": "meta_analysis"
        }

class EvidenceGapDetector:
    """Detects gaps in evidence substrate"""
    
    def __init__(self):
        self.gap_types = [
            "temporal_gaps",
            "domain_gaps",
            "methodological_gaps",
            "population_gaps",
            "quality_gaps"
        ]
    
    def identify_gaps(
        self,
        domain: str,
        context: Dict[str, Any],
        quality_assessment: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Identify evidence gaps"""
        
        gaps = []
        
        # Check for temporal gaps
        temporal_gaps = self._identify_temporal_gaps(domain, context)
        gaps.extend(temporal_gaps)
        
        # Check for domain gaps
        domain_gaps = self._identify_domain_gaps(domain, context)
        gaps.extend(domain_gaps)
        
        # Check for methodological gaps
        methodological_gaps = self._identify_methodological_gaps(domain, context)
        gaps.extend(methodological_gaps)
        
        # Check for quality gaps
        quality_gaps = self._identify_quality_gaps(quality_assessment)
        gaps.extend(quality_gaps)
        
        return gaps
    
    def _identify_temporal_gaps(
        self,
        domain: str,
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Identify temporal gaps in evidence"""
        
        gaps = []
        
        # Get evidence timeline
        evidence_timeline = self._get_evidence_timeline(domain)
        
        # Check for recent evidence gaps
        recent_cutoff = datetime.now() - timedelta(days=365)
        recent_evidence = [e for e in evidence_timeline if e.created_at > recent_cutoff]
        
        if len(recent_evidence) < len(evidence_timeline) * 0.2:
            gaps.append({
                "gap_type": "temporal_gaps",
                "description": "Insufficient recent evidence",
                "severity": "high",
                "recommended_action": "Generate current evidence through experiments or data collection",
                "impact_areas": ["decision_making", "relevance"]
            })
        
        return gaps
    
    def _identify_domain_gaps(
        self,
        domain: str,
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Identify domain coverage gaps"""
        
        gaps = []
        
        # Get domain coverage map
        domain_coverage = self._get_domain_coverage(domain)
        
        # Check for underrepresented subdomains
        for subdomain, coverage in domain_coverage.items():
            if coverage < 0.3:  # Less than 30% coverage
                gaps.append({
                    "gap_type": "domain_gaps",
                    "description": f"Insufficient evidence in subdomain: {subdomain}",
                    "severity": "medium",
                    "recommended_action": f"Focus research on {subdomain}",
                    "impact_areas": [subdomain],
                    "coverage_percentage": coverage
                })
        
        return gaps

class EvidenceBasedDecisionMaker:
    """Makes decisions based on evidence analysis"""
    
    def __init__(self):
        self.evidence_optimizer = EvidenceSubstrateOptimizer()
        self.decision_framework = EvidenceDecisionFramework()
        
    def make_evidence_based_decision(
        self,
        research_question: str,
        context: Dict[str, Any]
    ) -> EvidenceBasedDecision:
        """Make decision based on evidence analysis"""
        
        # Optimize evidence substrate
        domain = context.get("domain", "general")
        evidence_optimization = self.evidence_optimizer.optimize_evidence_substrate(
            domain, context
        )
        
        # Generate decision based on evidence
        decision = self.decision_framework.generate_decision(
            research_question, evidence_optimization, context
        )
        
        return decision

## Veklom-Specific Applications

### 1. Scientist Agent Enhancement
- **Evidence Quality Focus**: Prioritize evidence quality over model capability
- **Domain-Specific Evidence**: Tailor evidence systems to each scientific domain
- **Evidence Gap Filling**: Proactively identify and fill evidence gaps

### 2. Research Pipeline Optimization
- **Evidence-Driven Hypotheses**: Generate hypotheses based on evidence gaps
- **Evidence Validation**: Use evidence validation to guide research direction
- **Evidence Synthesis**: Combine evidence from multiple sources effectively

### 3. Decision Making Improvement
- **Evidence-Weighted Decisions**: Weight decisions by evidence quality and quantity
- **Uncertainty Quantification**: Explicitly quantify uncertainty in evidence
- **Alternative Hypothesis Generation**: Generate alternatives based on evidence gaps

## Success Metrics

| Metric | Target | Evidence-Based Focus |
|---|---|---|
| Evidence quality score | > 0.8 | Quality over quantity |
| Evidence gap reduction | > 50% | Proactive gap filling |
| Decision confidence | > 0.9 | Evidence-driven confidence |
| Evidence synthesis accuracy | > 95% | Reliable synthesis |
| Research efficiency | +40% | Evidence-optimized research |

## Dependencies

- Agent-063 (research lead)
- Agent-065 (memory scientist - for evidence storage)
- Agent-072 (evidence scientist - for evidence validation)
- Agent-073 (conjecture scientist - for evidence-based hypotheses)
- All domain scientists (for domain-specific evidence)

---

## Research References

1. **AI Scientists Are Only as Good as Their Evidence** (arXiv:2606.09556)
2. **Moonshine**: Autonomous Mathematical Research Agent (arXiv:2606.10806)
3. **WebChallenger**: Reliable and Efficient Generalist Web Agent (arXiv:2606.10423)
