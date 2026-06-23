from dataclasses import dataclass, field


@dataclass
class CheckResult:
    name: str
    passed: bool
    severity: str
    summary: str
    details: dict = field(default_factory=dict)
