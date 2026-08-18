"""Dependency-source regressions for the AWS SDK / urllib3 security boundary."""

from pathlib import Path


EXPECTED = {
    "aioboto3": "15.5.0",
    "boto3": "1.40.61",
    "botocore": "1.40.61",
    "s3transfer": "0.14.0",
    "urllib3": "2.7.0",
}


def _requirements() -> dict[str, str]:
    resolved: dict[str, str] = {}
    for raw in Path("requirements.txt").read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "==" not in line:
            continue
        name, version = line.split("==", 1)
        resolved[name.lower()] = version
    return resolved


def test_aws_sdk_family_and_urllib3_are_explicitly_pinned():
    requirements = _requirements()
    for package, version in EXPECTED.items():
        assert requirements.get(package) == version


def test_urllib3_is_never_left_as_a_bare_direct_dependency():
    lines = {
        line.strip().lower()
        for line in Path("requirements.txt").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    assert "urllib3" not in lines
