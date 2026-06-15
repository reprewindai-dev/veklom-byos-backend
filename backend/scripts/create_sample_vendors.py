"""Script to create sample vendors and marketplace listings."""

import asyncio
import sys
import os
from datetime import datetime, timezone

# Add the backend directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

# Import with proper path handling
try:
    from backend.core.database.database import get_db_url
    from backend.core.config.settings import settings
    from backend.db.models.marketplace import MarketplaceListing, Vendor
    from backend.db.models.user import User
    from backend.db.models.referral import ReferralCode
except ImportError:
    # Fallback for direct execution
    sys.path.append(os.path.dirname(__file__))
    from core.database.database import get_db_url
    from core.config.settings import settings
    from db.models.marketplace import MarketplaceListing, Vendor
    from db.models.user import User
    from db.models.referral import ReferralCode

import uuid


# Sample vendor data
SAMPLE_VENDORS = [
    {
        "business_name": "AI Security Labs",
        "user_email": "vendor1@aisecuritylabs.com",
        "description": "Leading provider of AI security and compliance solutions"
    },
    {
        "business_name": "DataFlow Analytics",
        "user_email": "vendor2@dataflow.com",
        "description": "Advanced data analytics and visualization tools"
    },
    {
        "business_name": "CloudOps Solutions",
        "user_email": "vendor3@cloudops.com",
        "description": "Enterprise cloud infrastructure and DevOps automation"
    },
    {
        "business_name": "ComplianceGuard Inc",
        "user_email": "vendor4@complianceguard.com",
        "description": "Automated compliance monitoring and reporting"
    },
    {
        "business_name": "NeuralTech Systems",
        "user_email": "vendor5@neuraltech.com",
        "description": "Cutting-edge neural network and ML model development"
    },
    {
        "business_name": "SecureData Corp",
        "user_email": "vendor6@securedata.com",
        "description": "Data encryption and privacy protection solutions"
    },
    {
        "business_name": "Workflow Automation Pro",
        "user_email": "vendor7@workflowpro.com",
        "description": "Business process automation and workflow optimization"
    },
    {
        "business_name": "API Gateway Masters",
        "user_email": "vendor8@apigateway.com",
        "description": "API management, monitoring, and security solutions"
    },
    {
        "business_name": "DevOps Toolkit Co",
        "user_email": "vendor9@devopstoolkit.com",
        "description": "Comprehensive DevOps tools and CI/CD pipelines"
    },
    {
        "business_name": "AI Monitoring Labs",
        "user_email": "vendor10@aimonitoring.com",
        "description": "AI model monitoring, performance tracking, and A/B testing"
    },
    {
        "business_name": "PrivacyFirst Solutions",
        "user_email": "vendor11@privacyfirst.com",
        "description": "Privacy-preserving analytics and data anonymization"
    },
    {
        "business_name": "Quantum Leap AI",
        "user_email": "vendor12@quantumleap.com",
        "description": "Next-generation AI algorithms and optimization frameworks"
    }
]

# Sample marketplace listings
SAMPLE_LISTINGS = [
    {
        "name": "Security Compliance Scanner",
        "category": "security",
        "description": "Automated security vulnerability scanner for code repositories and cloud infrastructure",
        "price": 0.50,
        "pricing_model": "per_scan",
        "tags": ["security", "compliance", "automation", "devops"],
        "icon_url": "https://cdn.veklom.com/icons/security-scanner.png"
    },
    {
        "name": "Data Anonymization Engine",
        "category": "privacy",
        "description": "Advanced PII detection and anonymization for GDPR/CCPA compliance",
        "price": 0.75,
        "pricing_model": "per_use",
        "tags": ["privacy", "gdpr", "ccpa", "data-protection"],
        "icon_url": "https://cdn.veklom.com/icons/privacy-engine.png"
    },
    {
        "name": "CI/CD Pipeline Optimizer",
        "category": "devops",
        "description": "AI-powered optimization for build and deployment pipelines",
        "price": 1.20,
        "pricing_model": "per_analysis",
        "tags": ["cicd", "devops", "optimization", "automation"],
        "icon_url": "https://cdn.veklom.com/icons/cicd-optimizer.png"
    },
    {
        "name": "ML Model Monitor",
        "category": "monitoring",
        "description": "Real-time monitoring and alerting for machine learning model performance",
        "price": 0.90,
        "pricing_model": "per_month",
        "tags": ["ml", "monitoring", "performance", "analytics"],
        "icon_url": "https://cdn.veklom.com/icons/ml-monitor.png"
    },
    {
        "name": "API Rate Limiter",
        "category": "infrastructure",
        "description": "Intelligent API rate limiting with burst protection and fair queuing",
        "price": 0.30,
        "pricing_model": "per_use",
        "tags": ["api", "infrastructure", "performance", "scaling"],
        "icon_url": "https://cdn.veklom.com/icons/api-limiter.png"
    },
    {
        "name": "Document Redaction Tool",
        "category": "privacy",
        "description": "Automated document redaction for legal and compliance purposes",
        "price": 0.60,
        "pricing_model": "per_document",
        "tags": ["legal", "privacy", "compliance", "automation"],
        "icon_url": "https://cdn.veklom.com/icons/document-redactor.png"
    },
    {
        "name": "Cloud Cost Optimizer",
        "category": "infrastructure",
        "description": "AI-powered cloud cost analysis and optimization recommendations",
        "price": 1.50,
        "pricing_model": "per_analysis",
        "tags": ["cloud", "cost", "optimization", "infrastructure"],
        "icon_url": "https://cdn.veklom.com/icons/cost-optimizer.png"
    },
    {
        "name": "Workflow Automation Engine",
        "category": "automation",
        "description": "No-code workflow automation for business processes",
        "price": 0.80,
        "pricing_model": "per_workflow",
        "tags": ["automation", "workflow", "business", "no-code"],
        "icon_url": "https://cdn.veklom.com/icons/workflow-engine.png"
    },
    {
        "name": "Code Quality Analyzer",
        "category": "development",
        "description": "Comprehensive code quality analysis with improvement suggestions",
        "price": 0.45,
        "pricing_model": "per_scan",
        "tags": ["development", "quality", "code-review", "best-practices"],
        "icon_url": "https://cdn.veklom.com/icons/code-analyzer.png"
    },
    {
        "name": "Incident Response Bot",
        "category": "monitoring",
        "description": "Automated incident detection, triage, and response coordination",
        "price": 1.00,
        "pricing_model": "per_incident",
        "tags": ["monitoring", "incident-response", "automation", "devops"],
        "icon_url": "https://cdn.veklom.com/icons/incident-bot.png"
    },
    {
        "name": "Data Pipeline Validator",
        "category": "data",
        "description": "Validate and test data pipelines for quality and performance",
        "price": 0.70,
        "pricing_model": "per_validation",
        "tags": ["data", "pipeline", "quality", "testing"],
        "icon_url": "https://cdn.veklom.com/icons/data-validator.png"
    },
    {
        "name": "Compliance Report Generator",
        "category": "compliance",
        "description": "Automated generation of compliance reports for various frameworks",
        "price": 0.85,
        "pricing_model": "per_report",
        "tags": ["compliance", "reporting", "automation", "audit"],
        "icon_url": "https://cdn.veklom.com/icons/compliance-reporter.png"
    },
    {
        "name": "API Documentation Generator",
        "category": "development",
        "description": "Auto-generate comprehensive API documentation from code",
        "price": 0.40,
        "pricing_model": "per_api",
        "tags": ["api", "documentation", "development", "automation"],
        "icon_url": "https://cdn.veklom.com/icons/api-docs.png"
    },
    {
        "name": "Performance Profiler",
        "category": "monitoring",
        "description": "Deep application performance profiling and bottleneck detection",
        "price": 0.95,
        "pricing_model": "per_profile",
        "tags": ["performance", "monitoring", "profiling", "optimization"],
        "icon_url": "https://cdn.veklom.com/icons/performance-profiler.png"
    },
    {
        "name": "Security Policy Enforcer",
        "category": "security",
        "description": "Enforce security policies across development and deployment pipelines",
        "price": 1.10,
        "pricing_model": "per_policy",
        "tags": ["security", "policy", "enforcement", "devops"],
        "icon_url": "https://cdn.veklom.com/icons/security-enforcer.png"
    }
]


async def create_sample_vendors_and_listings():
    """Create sample vendors and marketplace listings."""
    
    # Create database engine
    engine = create_async_engine(get_db_url())
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as db:
        try:
            vendors_created = []
            listings_created = []
            
            # Create vendors
            for vendor_data in SAMPLE_VENDORS:
                # Check if vendor already exists
                existing_user = await db.execute(
                    select(User).where(User.email == vendor_data["user_email"])
                )
                user = existing_user.scalar_one_or_none()
                
                if not user:
                    # Create user for vendor
                    user = User(
                        email=vendor_data["user_email"],
                        hashed_password="$2b$12$dummy_hash_for_sample",
                        full_name=vendor_data["business_name"],
                        role="USER",
                        status="ACTIVE",
                        workspace_id=str(uuid.uuid4())  # Create dummy workspace
                    )
                    db.add(user)
                    await db.flush()
                
                # Check if vendor already exists
                existing_vendor = await db.execute(
                    select(Vendor).where(Vendor.user_id == user.id)
                )
                vendor = existing_vendor.scalar_one_or_none()
                
                if not vendor:
                    # Create vendor
                    vendor = Vendor(
                        user_id=user.id,
                        business_name=vendor_data["business_name"],
                        status="active",
                        onboarding_complete=True,
                        total_revenue=0.0,
                        stripe_account_id=f"acct_sample_{user.id[:8]}"
                    )
                    db.add(vendor)
                    await db.flush()
                
                vendors_created.append(vendor)
                
                # Create referral code for vendor
                existing_referral = await db.execute(
                    select(ReferralCode).where(ReferralCode.user_id == user.id)
                )
                if not existing_referral.scalar_one_or_none():
                    referral_code = ReferralCode(
                        user_id=user.id,
                        code=f"VEK{user.id[:8].upper()}{uuid.uuid4().hex[:6].upper()}",
                        reward_type="percentage",
                        reward_value=10.0,
                        max_uses=100
                    )
                    db.add(referral_code)
            
            # Create marketplace listings
            for i, listing_data in enumerate(SAMPLE_LISTINGS):
                # Assign to vendor in round-robin fashion
                vendor = vendors_created[i % len(vendors_created)]
                
                # Check if listing already exists
                existing_listing = await db.execute(
                    select(MarketplaceListing).where(
                        MarketplaceListing.vendor_id == vendor.id,
                        MarketplaceListing.name == listing_data["name"]
                    )
                )
                if not existing_listing.scalar_one_or_none():
                    listing = MarketplaceListing(
                        vendor_id=vendor.id,
                        workspace_id=vendor.user_id,  # Use user's workspace
                        name=listing_data["name"],
                        description=listing_data["description"],
                        category=listing_data["category"],
                        price=listing_data["price"],
                        pricing_model=listing_data["pricing_model"],
                        icon_url=listing_data["icon_url"],
                        status="published",
                        tags=listing_data["tags"],
                        downloads=0,
                        rating=0.0
                    )
                    db.add(listing)
                    listings_created.append(listing)
            
            await db.commit()
            
            print(f"✅ Created {len(vendors_created)} vendors")
            print(f"✅ Created {len(listings_created)} marketplace listings")
            print("\nVendors created:")
            for vendor in vendors_created:
                print(f"  - {vendor.business_name} (ID: {vendor.id})")
            
            print("\nListings created:")
            for listing in listings_created:
                print(f"  - {listing.name} ({listing.category}) - ${listing.price}")
            
        except Exception as e:
            await db.rollback()
            print(f"❌ Error: {str(e)}")
            raise


if __name__ == "__main__":
    asyncio.run(create_sample_vendors_and_listings())
