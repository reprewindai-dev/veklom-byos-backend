"""Tests for Genome Service."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession
from backend.core.services.genome_service import GenomeService, compute_genome_hashes, make_json_patch
from backend.db.models.genome import GenomeVersion


def test_compute_genome_hashes_deterministic():
    payload1 = {
        "model_layer": {"model": "gpt-4o-mini", "temperature": 0.7},
        "prompt_layer": {"system_prompt": "Prompt 1"},
        "policy_layer": {"max_tokens": 1000},
        "watchtower_layer": {"rules": []},
        "task_profile": {"task_type": "general"}
    }
    
    payload2 = {
        "model_layer": {"model": "gpt-4o-mini", "temperature": 0.7},
        "prompt_layer": {"system_prompt": "Prompt 1"},
        "policy_layer": {"max_tokens": 1000},
        "watchtower_layer": {"rules": []},
        "task_profile": {"task_type": "general"}
    }
    
    hashes1, root1 = compute_genome_hashes(payload1)
    hashes2, root2 = compute_genome_hashes(payload2)
    
    assert root1 == root2
    assert hashes1 == hashes2


def test_compute_genome_hashes_different():
    payload1 = {
        "model_layer": {"model": "gpt-4o-mini", "temperature": 0.7},
        "prompt_layer": {"system_prompt": "Prompt 1"},
    }
    
    payload2 = {
        "model_layer": {"model": "gpt-4o-mini", "temperature": 0.9}, # changed temperature
        "prompt_layer": {"system_prompt": "Prompt 1"},
    }
    
    _, root1 = compute_genome_hashes(payload1)
    _, root2 = compute_genome_hashes(payload2)
    
    assert root1 != root2


def test_make_json_patch():
    dict_a = {"a": 1, "b": 2, "nested": {"c": 3}}
    dict_b = {"a": 1, "b": 20, "nested": {"c": 3, "d": 4}}
    
    patches = make_json_patch(dict_a, dict_b)
    
    # Expect a replace for b, and add for d
    replace_b = [p for p in patches if p["op"] == "replace" and p["path"] == "/b"]
    add_d = [p for p in patches if p["op"] == "add" and p["path"] == "/nested/d"]
    
    assert len(replace_b) == 1
    assert replace_b[0]["value"] == 20
    assert len(add_d) == 1
    assert add_d[0]["value"] == 4


def test_diff_genomes():
    # Setup test mock genomes
    genome_a = MagicMock(spec=GenomeVersion)
    genome_b = MagicMock(spec=GenomeVersion)
    
    genome_a.merkle_root = "root_a"
    genome_b.merkle_root = "root_b"
    
    genome_a.model_layer_hash = "h1"
    genome_b.model_layer_hash = "h1_changed"
    
    genome_a.prompt_layer_hash = "h2"
    genome_b.prompt_layer_hash = "h2"
    
    genome_a.policy_layer_hash = "h3"
    genome_b.policy_layer_hash = "h3"
    
    genome_a.watchtower_layer_hash = "h4"
    genome_b.watchtower_layer_hash = "h4"
    
    genome_a.task_profile_hash = "h5"
    genome_b.task_profile_hash = "h5"
    
    genome_a.payload = {"model_layer": {"temp": 0.7}}
    genome_b.payload = {"model_layer": {"temp": 0.9}}
    
    diff = GenomeService.diff_genomes(genome_a, genome_b)
    
    assert "model_layer" in diff["changed_layers"]
    assert len(diff["changed_layers"]) == 1
    assert not diff["identical"]
    assert len(diff["patches"]["model_layer"]) == 1
    assert diff["patches"]["model_layer"][0]["op"] == "replace"
    assert diff["patches"]["model_layer"][0]["value"] == 0.9


@pytest.mark.asyncio
async def test_resolve_or_create_existing():
    db = AsyncMock(spec=AsyncSession)
    
    # Mocking select query results
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = MagicMock(spec=GenomeVersion, merkle_root="root_abc")
    db.execute.return_value = mock_result
    
    payload = {"model_layer": {"model": "gpt-4"}}
    
    result = await GenomeService.resolve_or_create(db, 1, payload)
    
    assert result is not None
    # Verify no commits were made since it existed
    db.commit.assert_not_called()
