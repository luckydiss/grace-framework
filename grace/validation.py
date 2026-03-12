from __future__ import annotations

from pathlib import Path

from grace.io import load_belief_state, load_contract
from grace.models import BeliefState, GraceModule, ModuleContract
from grace.parser import parse_python_module


class GraceValidationError(ValueError):
    pass


def validate_module_set(paths: list[str | Path]) -> tuple[list[GraceModule], list[ModuleContract], list[BeliefState]]:
    modules: list[GraceModule] = []
    contracts: list[ModuleContract] = []
    beliefs: list[BeliefState] = []
    seen_anchor_ids: set[str] = set()

    for path in paths:
        module, belief_paths = parse_python_module(path)
        contract = load_contract(module.contract_path)

        if contract.module_id != module.id:
            raise GraceValidationError(
                f"contract module_id {contract.module_id!r} does not match module {module.id!r}"
            )

        module_anchor_ids = {anchor.id for anchor in module.anchors}
        if set(contract.anchor_ids) != module_anchor_ids:
            raise GraceValidationError(
                f"contract anchors for {module.id!r} do not match implementation anchors"
            )

        for anchor in module.anchors:
            if anchor.id in seen_anchor_ids:
                raise GraceValidationError(f"duplicate anchor id {anchor.id!r}")
            seen_anchor_ids.add(anchor.id)

        for anchor_id, belief_path in belief_paths.items():
            belief = load_belief_state(belief_path)
            if belief.anchor_id != anchor_id:
                raise GraceValidationError(
                    f"belief anchor_id {belief.anchor_id!r} does not match declared anchor {anchor_id!r}"
                )
            beliefs.append(belief)

        complex_anchor_ids = {belief.anchor_id for belief in beliefs if belief.complexity == "complex"}
        for anchor in module.anchors:
            if anchor.id in complex_anchor_ids and not anchor.has_belief_state:
                raise GraceValidationError(f"complex anchor {anchor.id!r} is missing BELIEF_STATE")

        modules.append(module)
        contracts.append(contract)

    return modules, contracts, beliefs
