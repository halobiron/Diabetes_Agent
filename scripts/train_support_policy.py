"""Train the next-support-step policy in the simulated environment and compare it to baselines.

Writes artifacts/support_policy.json and artifacts/policy_comparison.json.
"""

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from rl.policy import (  # noqa: E402
    evaluate,
    fixed_full_policy,
    fixed_risk_policy,
    make_random_policy,
    train_q_learning,
)

ARTIFACTS = PROJECT_ROOT / "artifacts"


def main():
    policy = train_q_learning()
    policy.save(ARTIFACTS / "support_policy.json")
    comparison = {
        "feedback": "simulated (see rl/environment.py for every assumption)",
        "q_learning": evaluate(policy),
        "fixed_full_checklist": evaluate(fixed_full_policy),
        "fixed_risk_only": evaluate(fixed_risk_policy),
        "random": evaluate(make_random_policy()),
    }
    (ARTIFACTS / "policy_comparison.json").write_text(
        json.dumps(comparison, indent=2), encoding="utf-8"
    )
    for name, result in comparison.items():
        if isinstance(result, dict):
            print(f"{name:22s}", result)


if __name__ == "__main__":
    main()
