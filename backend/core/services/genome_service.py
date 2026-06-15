import hashlib
import json
from typing import Dict, Any, Tuple, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.db.models.genome import GenomeVersion

# In-process cache: merkle_root -> GenomeVersion
_genome_cache: Dict[str, GenomeVersion] = {}

def _canonical_hash(obj: Any) -> str:
    """Canonicalize a JSON-serializable object and compute its SHA-256 hash."""
    canonical_str = json.dumps(obj, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(canonical_str.encode('utf-8')).hexdigest()

def compute_genome_hashes(payload: Dict[str, Any]) -> Tuple[Dict[str, str], str]:
    """
    Decompose a genome payload into 5 layers, hash each, and calculate
    the Merkle root.
    """
    # Extract five layers (with fallbacks if flat payload)
    model_layer = payload.get("model_layer") or payload.get("model_config") or {}
    prompt_layer = payload.get("prompt_layer") or payload.get("prompt_config") or {}
    policy_layer = payload.get("policy_layer") or payload.get("policy_config") or {}
    watchtower_layer = payload.get("watchtower_layer") or payload.get("watchtower_config") or {}
    task_profile = payload.get("task_profile") or {}

    # Compute individual layer hashes
    model_hash = _canonical_hash(model_layer)
    prompt_hash = _canonical_hash(prompt_layer)
    policy_hash = _canonical_hash(policy_layer)
    watchtower_hash = _canonical_hash(watchtower_layer)
    task_hash = _canonical_hash(task_profile)

    # Standard Binary Merkle Tree logic with duplicate/propagate for odd nodes
    # Leaves: model, prompt, policy, watchtower, task
    # Level 1 pairs:
    h12 = hashlib.sha256((model_hash + prompt_hash).encode('utf-8')).hexdigest()
    h34 = hashlib.sha256((policy_hash + watchtower_hash).encode('utf-8')).hexdigest()
    h55 = hashlib.sha256((task_hash + task_hash).encode('utf-8')).hexdigest()

    # Level 2 pairs:
    h1234 = hashlib.sha256((h12 + h34).encode('utf-8')).hexdigest()
    h5555 = hashlib.sha256((h55 + h55).encode('utf-8')).hexdigest()

    # Level 3: Merkle Root
    merkle_root = hashlib.sha256((h1234 + h5555).encode('utf-8')).hexdigest()

    layer_hashes = {
        "model_layer_hash": model_hash,
        "prompt_layer_hash": prompt_hash,
        "policy_layer_hash": policy_hash,
        "watchtower_layer_hash": watchtower_hash,
        "task_profile_hash": task_hash
    }
    return layer_hashes, merkle_root

def make_json_patch(val_a: Any, val_b: Any, path: str = "") -> List[Dict[str, Any]]:
    """Generate RFC 6902 style JSON patches representing the differences between val_a and val_b."""
    patches = []
    if isinstance(val_a, dict) and isinstance(val_b, dict):
        for k in val_a:
            if k not in val_b:
                patches.append({"op": "remove", "path": f"{path}/{k}"})
            else:
                patches.extend(make_json_patch(val_a[k], val_b[k], f"{path}/{k}"))
        for k in val_b:
            if k not in val_a:
                patches.append({"op": "add", "path": f"{path}/{k}", "value": val_b[k]})
    elif isinstance(val_a, list) and isinstance(val_b, list):
        if val_a != val_b:
            patches.append({"op": "replace", "path": path, "value": val_b})
    else:
        if val_a != val_b:
            patches.append({"op": "replace", "path": path, "value": val_b})
    return patches

class GenomeService:
    """Service to manage PGL Genome configuration registration, caching, hashing, and diffing."""

    @staticmethod
    def compute_genome_hash(payload: Dict[str, Any]) -> str:
        """Compute the Merkle root hash of the genome payload."""
        _, merkle_root = compute_genome_hashes(payload)
        return merkle_root

    @staticmethod
    async def resolve_or_create(
        db: AsyncSession,
        agent_id: int,
        payload: Dict[str, Any],
        note: Optional[str] = None,
        parent_genome_ids: Optional[List[int]] = None
    ) -> GenomeVersion:
        """
        Check in-process cache and DB for existing genome version by merkle root.
        Create a new GenomeVersion in DB if not found.
        """
        layer_hashes, merkle_root = compute_genome_hashes(payload)

        # Check Cache
        if merkle_root in _genome_cache:
            return _genome_cache[merkle_root]

        # Check DB
        query = select(GenomeVersion).where(GenomeVersion.merkle_root == merkle_root)
        result = await db.execute(query)
        existing = result.scalar_one_or_none()

        if existing:
            _genome_cache[merkle_root] = existing
            return existing

        # Fetch latest version to compute next version number
        version_query = select(GenomeVersion).where(GenomeVersion.agent_id == agent_id).order_by(GenomeVersion.version.desc())
        version_result = await db.execute(version_query)
        latest = version_result.scalars().first()
        next_version = (latest.version + 1) if latest else 1

        # Create new genome version
        new_genome = GenomeVersion(
            agent_id=agent_id,
            version=next_version,
            payload=payload,
            genome_hash=merkle_root, # backward compatibility
            note=note,
            model_layer_hash=layer_hashes["model_layer_hash"],
            prompt_layer_hash=layer_hashes["prompt_layer_hash"],
            policy_layer_hash=layer_hashes["policy_layer_hash"],
            watchtower_layer_hash=layer_hashes["watchtower_layer_hash"],
            task_profile_hash=layer_hashes["task_profile_hash"],
            merkle_root=merkle_root,
            parent_genome_ids=parent_genome_ids
        )

        db.add(new_genome)
        await db.commit()
        await db.refresh(new_genome)

        _genome_cache[merkle_root] = new_genome
        return new_genome

    @staticmethod
    def diff_genomes(genome_a: GenomeVersion, genome_b: GenomeVersion) -> Dict[str, Any]:
        """
        Compare two genome configurations leaf by leaf.
        Returns a dict indicating which layers changed, along with RFC 6902 JSON patches.
        """
        changed_layers = []
        patches = {}

        layers = [
            ("model_layer", "model_layer_hash"),
            ("prompt_layer", "prompt_layer_hash"),
            ("policy_layer", "policy_layer_hash"),
            ("watchtower_layer", "watchtower_layer_hash"),
            ("task_profile", "task_profile_hash")
        ]

        payload_a = genome_a.payload
        payload_b = genome_b.payload

        for layer_key, hash_col in layers:
            hash_a = getattr(genome_a, hash_col, None)
            hash_b = getattr(genome_b, hash_col, None)

            if hash_a != hash_b:
                changed_layers.append(layer_key)
                # Compute diff on the payload section
                data_a = payload_a.get(layer_key) or {}
                data_b = payload_b.get(layer_key) or {}
                patches[layer_key] = make_json_patch(data_a, data_b)

        return {
            "changed_layers": changed_layers,
            "patches": patches,
            "identical": len(changed_layers) == 0,
            "merkle_root_a": genome_a.merkle_root,
            "merkle_root_b": genome_b.merkle_root
        }
