from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest


SCRIPT = Path(__file__).parents[2] / "scripts" / "ci" / "verify_alembic_head.py"
SPEC = spec_from_file_location("verify_alembic_head", SCRIPT)
assert SPEC and SPEC.loader
MODULE = module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
validate_single_head = MODULE.validate_single_head


def test_matching_single_head_is_accepted():
    assert validate_single_head(["revision_2"], ["revision_2"]) == "revision_2"


@pytest.mark.parametrize(
    ("code_heads", "database_heads", "message"),
    [
        ([], ["revision_2"], "code has no head revision"),
        (["revision_1", "revision_2"], ["revision_1", "revision_2"], "exactly one head"),
        (["revision_1", "revision_2"], ["revision_2"], "exactly one head"),
        (["revision_2"], [], "database has no recorded revision"),
        (["revision_2"], ["revision_1", "revision_2"], "exactly one recorded revision"),
        (["revision_2"], ["revision_1"], "does not match code head"),
    ],
)
def test_invalid_head_states_are_rejected(code_heads, database_heads, message):
    with pytest.raises(SystemExit, match=message):
        validate_single_head(code_heads, database_heads)
