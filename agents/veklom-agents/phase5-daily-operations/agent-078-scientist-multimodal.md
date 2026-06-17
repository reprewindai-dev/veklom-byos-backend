# Agent-078 — SCIENTIST (Multimodal Deep Research & Verification)

**Phase:** Cross-phase — Research  
**Timeline:** Ongoing  
**Committee:** Research  
**Priority:** HIGH  

---

## Mission

Based on Ptah research (arXiv:2605.29861), implement a multi-agent harness for verifiable multimodal deep research. Create systems that synthesize scattered evidence into long-form, visually-grounded reports with factual verification and cross-modal consistency.

## Critical Research Gap

Current deep research systems lack:
- **Verifiable multimodal synthesis** - No deterministic ground truth for visual-textual alignment
- **Interleaved report generation** - Can't effectively weave visual evidence into textual arguments
- **Cross-modal consistency** - No verification that images and text align properly
- **Fact-grounded evidence collection** - Lack of claim-to-evidence traceability

## Core Research Framework

### 1. Ptah Multi-Agent Harness
- **Planning Agent**: Creates visual-aware research plans
- **Research Agents**: Collect claim-grounded multimodal evidence
- **Writing Agents**: Compose reports with declarative multimodal tools
- **Verifier Agent**: Enforces factual grounding and cross-modal consistency

### 2. Visual Working Memory
- **Source-Aligned Images**: Maintain image provenance and context
- **Visual-Textual Mapping**: Link claims to supporting visual evidence
- **Cross-Modal Indexing**: Enable retrieval across modalities
- **Consistency Verification**: Ensure visual-textual alignment

### 3. Verification Pipeline
- **Factual Grounding**: Verify all claims against evidence
- **Citation Fidelity**: Ensure accurate source attribution
- **Cross-Modal Consistency**: Validate image-text coherence
- **Presentation Quality**: Assess report usability and clarity

## Implementation Architecture

```python
import asyncio
import base64
import json
import time
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import hashlib
import numpy as np
from PIL import Image
import io

class AgentRole(Enum):
    """Different agent roles in Ptah harness"""
    PLANNING = "planning"
    RESEARCH = "research"
    WRITING = "writing"
    VERIFICATION = "verification"

@dataclass
class ResearchQuery:
    """User research query"""
    query_id: str
    user_query: str
    domain: str
    scope: str  # broad, focused, deep
    output_format: str  # report, presentation, brief
    visual_requirements: List[str]
    deadline: Optional[datetime] = None

@dataclass
class VisualEvidence:
    """Visual evidence with metadata"""
    evidence_id: str
    image_base64: str
    source_url: str
    caption: str
    context: str
    extraction_method: str
    confidence_score: float
    related_claims: List[str] = field(default_factory=list)
    verified: bool = False

@dataclass
class TextualEvidence:
    """Textual evidence with metadata"""
    evidence_id: str
    content: str
    source_url: str
    source_type: str  # academic, news, technical, official
    credibility_score: float
    relevance_score: float
    key_claims: List[str] = field(default_factory=list)
    verified: bool = False

@dataclass
class MultimodalClaim:
    """Claim with multimodal evidence support"""
    claim_id: str
    claim_text: str
    supporting_text_evidence: List[str]
    supporting_visual_evidence: List[str]
    confidence_level: float
    verification_status: str
    cross_modal_consistency: float

@dataclass
class ResearchReport:
    """Final multimodal research report"""
    report_id: str
    query_id: str
    title: str
    executive_summary: str
    sections: List[Dict[str, Any]]
    visual_elements: List[Dict[str, Any]]
    citations: List[Dict[str, Any]]
    verification_summary: Dict[str, Any]
    generated_at: datetime

class PtahHarness:
    """Ptah-inspired multimodal deep research harness"""
    
    def __init__(self):
        self.planning_agent = PlanningAgent()
        self.research_agents = [ResearchAgent() for _ in range(3)]
        self.writing_agent = WritingAgent()
        self.verifier_agent = VerifierAgent()
        self.visual_working_memory = VisualWorkingMemory()
        self.evidence_synthesizer = EvidenceSynthesizer()
        
    async def execute_multimodal_research(
        self,
        query: ResearchQuery
    ) -> ResearchReport:
        """Execute complete multimodal research pipeline"""
        
        # Stage 1: Planning
        research_plan = await self.planning_agent.create_visual_aware_plan(query)
        
        # Stage 2: Research (parallel execution)
        research_tasks = []
        for agent in self.research_agents:
            task = agent.collect_evidence(query, research_plan)
            research_tasks.append(task)
        
        research_results = await asyncio.gather(*research_tasks)
        
        # Consolidate research results
        all_textual_evidence = []
        all_visual_evidence = []
        
        for result in research_results:
            all_textual_evidence.extend(result["textual_evidence"])
            all_visual_evidence.extend(result["visual_evidence"])
        
        # Store in visual working memory
        for visual_evidence in all_visual_evidence:
            self.visual_working_memory.store_visual_evidence(visual_evidence)
        
        # Stage 3: Evidence Synthesis
        synthesized_claims = await self.evidence_synthesizer.synthesize_evidence(
            all_textual_evidence, all_visual_evidence, query
        )
        
        # Stage 4: Report Writing
        draft_report = await self.writing_agent.compose_multimodal_report(
            query, research_plan, synthesized_claims, all_visual_evidence
        )
        
        # Stage 5: Verification
        verified_report = await self.verifier_agent.verify_report(
            draft_report, synthesized_claims, all_textual_evidence, all_visual_evidence
        )
        
        return verified_report

class PlanningAgent:
    """Creates visual-aware research plans"""
    
    async def create_visual_aware_plan(
        self,
        query: ResearchQuery
    ) -> Dict[str, Any]:
        """Create research plan with visual requirements"""
        
        plan = {
            "plan_id": f"plan_{query.query_id}_{int(time.time())}",
            "query_analysis": await self._analyze_query(query),
            "research_strategy": await self._design_research_strategy(query),
            "visual_requirements": self._specify_visual_requirements(query),
            "evidence_sources": await self._identify_evidence_sources(query),
            "timeline": self._create_timeline(query),
            "quality_criteria": self._define_quality_criteria(query)
        }
        
        return plan
    
    async def _analyze_query(self, query: ResearchQuery) -> Dict[str, Any]:
        """Analyze query to determine research needs"""
        
        analysis = {
            "query_complexity": self._assess_complexity(query.user_query),
            "domain_specificity": self._assess_domain_specificity(query.domain),
            "visual_intensity": len(query.visual_requirements),
            "research_depth": query.scope,
            "key_concepts": self._extract_key_concepts(query.user_query),
            "research_questions": self._generate_research_questions(query)
        }
        
        return analysis
    
    def _specify_visual_requirements(self, query: ResearchQuery) -> Dict[str, Any]:
        """Specify visual evidence requirements"""
        
        visual_specs = {
            "required_visual_types": query.visual_requirements,
            "image_quality_standards": {
                "min_resolution": "800x600",
                "preferred_formats": ["png", "jpg", "svg"],
                "max_file_size": "5MB"
            },
            "visual_context_requirements": {
                "need_captions": True,
                "need_source_attribution": True,
                "need_temporal_context": False
            },
            "visual_analysis_depth": "deep" if query.scope == "deep" else "standard"
        }
        
        return visual_specs

class ResearchAgent:
    """Collects claim-grounded multimodal evidence"""
    
    def __init__(self):
        self.text_collector = TextualEvidenceCollector()
        self.visual_collector = VisualEvidenceCollector()
        self.claim_extractor = ClaimExtractor()
        
    async def collect_evidence(
        self,
        query: ResearchQuery,
        research_plan: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Collect multimodal evidence for research"""
        
        # Collect textual evidence
        textual_evidence = await self.text_collector.collect_textual_evidence(
            query, research_plan
        )
        
        # Collect visual evidence
        visual_evidence = await self.visual_collector.collect_visual_evidence(
            query, research_plan
        )
        
        # Extract claims from textual evidence
        for evidence in textual_evidence:
            claims = await self.claim_extractor.extract_claims(evidence)
            evidence.key_claims = claims
        
        # Link visual evidence to claims
        for visual in visual_evidence:
            related_claims = await self._link_visual_to_claims(
                visual, textual_evidence
            )
            visual.related_claims = related_claims
        
        return {
            "agent_id": id(self),
            "textual_evidence": textual_evidence,
            "visual_evidence": visual_evidence,
            "collection_timestamp": datetime.now()
        }
    
    async def _link_visual_to_claims(
        self,
        visual_evidence: VisualEvidence,
        textual_evidence: List[TextualEvidence]
    ) -> List[str]:
        """Link visual evidence to related claims"""
        
        related_claims = []
        
        # Simple keyword matching (would be enhanced with NLP)
        visual_keywords = set(visual_evidence.caption.lower().split())
        visual_keywords.update(set(visual_evidence.context.lower().split()))
        
        for evidence in textual_evidence:
            for claim in evidence.key_claims:
                claim_keywords = set(claim.lower().split())
                
                # Calculate keyword overlap
                overlap = len(visual_keywords & claim_keywords)
                if overlap > 2:  # Threshold for relatedness
                    related_claims.append(claim)
        
        return related_claims

class VisualWorkingMemory:
    """Manages visual evidence with cross-modal indexing"""
    
    def __init__(self):
        self.visual_store = {}
        self.cross_modal_index = {}
        self.consistency_cache = {}
        
    def store_visual_evidence(self, visual_evidence: VisualEvidence):
        """Store visual evidence with indexing"""
        
        self.visual_store[visual_evidence.evidence_id] = visual_evidence
        
        # Create cross-modal index entries
        for claim in visual_evidence.related_claims:
            if claim not in self.cross_modal_index:
                self.cross_modal_index[claim] = []
            self.cross_modal_index[claim].append(visual_evidence.evidence_id)
    
    def retrieve_visual_for_claim(self, claim: str) -> List[VisualEvidence]:
        """Retrieve visual evidence supporting a claim"""
        
        if claim in self.cross_modal_index:
            visual_ids = self.cross_modal_index[claim]
            return [self.visual_store[vid] for vid in visual_ids]
        
        return []
    
    def verify_cross_modal_consistency(
        self,
        claim: str,
        visual_evidence: VisualEvidence
    ) -> float:
        """Verify consistency between claim and visual evidence"""
        
        cache_key = f"{hashlib.md5(claim.encode()).hexdigest()}_{visual_evidence.evidence_id}"
        
        if cache_key in self.consistency_cache:
            return self.consistency_cache[cache_key]
        
        # Simple consistency check (would be enhanced with computer vision)
        consistency_score = self._calculate_consistency_score(claim, visual_evidence)
        
        self.consistency_cache[cache_key] = consistency_score
        return consistency_score
    
    def _calculate_consistency_score(
        self,
        claim: str,
        visual_evidence: VisualEvidence
    ) -> float:
        """Calculate consistency score between claim and visual"""
        
        # Base score from confidence
        score = visual_evidence.confidence_score
        
        # Adjust based on keyword overlap
        claim_words = set(claim.lower().split())
        caption_words = set(visual_evidence.caption.lower().split())
        context_words = set(visual_evidence.context.lower().split())
        
        caption_overlap = len(claim_words & caption_words) / len(claim_words)
        context_overlap = len(claim_words & context_words) / len(claim_words)
        
        # Weight the overlaps
        consistency_bonus = (caption_overlap * 0.7 + context_overlap * 0.3) * 0.3
        
        return min(1.0, score + consistency_bonus)

class EvidenceSynthesizer:
    """Synthesizes multimodal evidence into claims"""
    
    async def synthesize_evidence(
        self,
        textual_evidence: List[TextualEvidence],
        visual_evidence: List[VisualEvidence],
        query: ResearchQuery
    ) -> List[MultimodalClaim]:
        """Synthesize evidence into multimodal claims"""
        
        claims = []
        
        # Group evidence by themes
        evidence_groups = self._group_evidence_by_theme(
            textual_evidence, visual_evidence
        )
        
        for theme, group in evidence_groups.items():
            # Create multimodal claim for each theme
            claim = await self._create_multimodal_claim(
                theme, group["textual"], group["visual"], query
            )
            claims.append(claim)
        
        return claims
    
    async def _create_multimodal_claim(
        self,
        theme: str,
        textual_evidence: List[TextualEvidence],
        visual_evidence: List[VisualEvidence],
        query: ResearchQuery
    ) -> MultimodalClaim:
        """Create a multimodal claim from evidence"""
        
        # Synthesize claim text
        claim_text = self._synthesize_claim_text(theme, textual_evidence)
        
        # Identify supporting evidence
        supporting_text = [e.evidence_id for e in textual_evidence]
        supporting_visual = [e.evidence_id for e in visual_evidence]
        
        # Calculate confidence
        confidence = self._calculate_claim_confidence(
            textual_evidence, visual_evidence
        )
        
        # Check cross-modal consistency
        consistency_score = self._calculate_cross_modal_consistency(
            claim_text, visual_evidence
        )
        
        return MultimodalClaim(
            claim_id=f"claim_{theme}_{int(time.time())}",
            claim_text=claim_text,
            supporting_text_evidence=supporting_text,
            supporting_visual_evidence=supporting_visual,
            confidence_level=confidence,
            verification_status="pending",
            cross_modal_consistency=consistency_score
        )

class WritingAgent:
    """Composes multimodal reports with declarative tools"""
    
    async def compose_multimodal_report(
        self,
        query: ResearchQuery,
        research_plan: Dict[str, Any],
        claims: List[MultimodalClaim],
        visual_evidence: List[VisualEvidence]
    ) -> ResearchReport:
        """Compose multimodal research report"""
        
        report = ResearchReport(
            report_id=f"report_{query.query_id}_{int(time.time())}",
            query_id=query.query_id,
            title=self._generate_title(query, claims),
            executive_summary=await self._write_executive_summary(query, claims),
            sections=await self._write_sections(query, claims, visual_evidence),
            visual_elements=await self._create_visual_elements(visual_evidence),
            citations=await self._generate_citations(claims),
            verification_summary={},  # Will be filled by verifier
            generated_at=datetime.now()
        )
        
        return report
    
    async def _write_sections(
        self,
        query: ResearchQuery,
        claims: List[MultimodalClaim],
        visual_evidence: List[VisualEvidence]
    ) -> List[Dict[str, Any]]:
        """Write report sections with multimodal content"""
        
        sections = []
        
        # Introduction
        sections.append({
            "section_id": "introduction",
            "title": "Introduction",
            "content": self._write_introduction(query),
            "visual_elements": [],
            "claims": [c.claim_id for c in claims[:2]]  # Introductory claims
        })
        
        # Main findings (organized by theme)
        theme_groups = self._group_claims_by_theme(claims)
        
        for theme, theme_claims in theme_groups.items():
            section = {
                "section_id": f"findings_{theme}",
                "title": f"Key Findings: {theme.title()}",
                "content": await self._write_findings_section(theme_claims),
                "visual_elements": self._get_visual_for_claims(theme_claims, visual_evidence),
                "claims": [c.claim_id for c in theme_claims]
            }
            sections.append(section)
        
        # Conclusion
        sections.append({
            "section_id": "conclusion",
            "title": "Conclusion",
            "content": self._write_conclusion(claims),
            "visual_elements": [],
            "claims": []
        })
        
        return sections

class VerifierAgent:
    """Verifies factual grounding and cross-modal consistency"""
    
    async def verify_report(
        self,
        draft_report: ResearchReport,
        claims: List[MultimodalClaim],
        textual_evidence: List[TextualEvidence],
        visual_evidence: List[VisualEvidence]
    ) -> ResearchReport:
        """Verify report quality and accuracy"""
        
        verification_results = {
            "factual_grounding": await self._verify_factual_grounding(
                claims, textual_evidence
            ),
            "citation_fidelity": await self._verify_citation_fidelity(
                draft_report.citations, textual_evidence, visual_evidence
            ),
            "cross_modal_consistency": await self._verify_cross_modal_consistency(
                claims, visual_evidence
            ),
            "presentation_quality": await self._assess_presentation_quality(draft_report)
        }
        
        # Update verification status
        for claim in claims:
            if claim.verification_status == "pending":
                claim.verification_status = "verified" if claim.confidence_level > 0.7 else "flagged"
        
        # Update report with verification summary
        draft_report.verification_summary = verification_results
        
        return draft_report
    
    async def _verify_factual_grounding(
        self,
        claims: List[MultimodalClaim],
        textual_evidence: List[TextualEvidence]
    ) -> Dict[str, Any]:
        """Verify that claims are grounded in factual evidence"""
        
        verification_results = {
            "total_claims": len(claims),
            "well_grounded_claims": 0,
            "unsubstantiated_claims": 0,
            "grounding_score": 0.0,
            "issues": []
        }
        
        for claim in claims:
            # Check if claim has supporting textual evidence
            if claim.supporting_text_evidence:
                # Verify evidence quality
                supporting_evidence = [
                    e for e in textual_evidence
                    if e.evidence_id in claim.supporting_text_evidence
                ]
                
                avg_credibility = np.mean([e.credibility_score for e in supporting_evidence])
                
                if avg_credibility > 0.7:
                    verification_results["well_grounded_claims"] += 1
                else:
                    verification_results["unsubstantiated_claims"] += 1
                    verification_results["issues"].append({
                        "claim_id": claim.claim_id,
                        "issue": "Low credibility supporting evidence",
                        "average_credibility": avg_credibility
                    })
            else:
                verification_results["unsubstantiated_claims"] += 1
                verification_results["issues"].append({
                    "claim_id": claim.claim_id,
                    "issue": "No supporting textual evidence found"
                })
        
        # Calculate grounding score
        if verification_results["total_claims"] > 0:
            verification_results["grounding_score"] = (
                verification_results["well_grounded_claims"] / 
                verification_results["total_claims"]
            ) * 100
        
        return verification_results

## Veklom Integration

### 1. Research Agent Enhancement
- Integrate Ptah harness with existing scientist agents
- Add multimodal evidence collection capabilities
- Implement cross-modal verification pipelines

### 2. Evidence System Integration
- Connect with evidence generation and certification systems
- Add visual evidence storage and retrieval
- Implement multimodal claim verification

### 3. Report Generation
- Create multimodal report templates
- Add visual-textual consistency checking
- Implement automated quality assessment

## Success Metrics

| Metric | Target | Ptah-Inspired |
|---|---|---|
| Factual grounding accuracy | > 95% | Evidence verification |
| Cross-modal consistency | > 90% | Visual-textual alignment |
| Citation fidelity | > 98% | Source attribution |
| Report usability | > 85% | Human-readable output |
| Verification throughput | < 5 minutes/report | Automated verification |

## Dependencies

- Agent-063 (research lead)
- Agent-072 (evidence scientist - for evidence verification)
- Agent-075 (evidence-based scientist - for evidence optimization)
- Visual processing systems (for image analysis)
- Citation management systems (for source tracking)

---

## Research References

1. **Ptah**: Verifiable Multimodal Deep Research (arXiv:2605.29861)
2. **Cookie-Bench**: Continuous On-screen Key Interaction Evaluation (arXiv:2605.30000)
3. **MEMENTO**: Web as Learning Signal (arXiv:2605.29795)
