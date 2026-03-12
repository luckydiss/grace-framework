from __future__ import annotations

from grace.models import BeliefState, GraceModule, ModuleContract


def build_graph_export(
    modules: list[GraceModule],
    contracts: list[ModuleContract],
    beliefs: list[BeliefState],
) -> dict:
    belief_by_anchor = {belief.anchor_id: belief for belief in beliefs}
    anchors = [anchor.to_dict() for module in modules for anchor in module.anchors]
    edges: list[dict[str, str]] = []

    for module in modules:
        edges.append(
            {
                "type": "module_has_contract",
                "source": module.id,
                "target": module.id,
            }
        )
        for anchor in module.anchors:
            edges.append(
                {
                    "type": "module_has_anchor",
                    "source": module.id,
                    "target": anchor.id,
                }
            )
            if anchor.id in belief_by_anchor:
                edges.append(
                    {
                        "type": "anchor_has_belief",
                        "source": anchor.id,
                        "target": anchor.id,
                    }
                )

    return {
        "modules": [
            {
                "id": module.id,
                "contract_path": str(module.contract_path),
            }
            for module in modules
        ],
        "contracts": [contract.to_dict() for contract in contracts],
        "anchors": anchors,
        "beliefs": [belief.to_dict() for belief in beliefs],
        "edges": edges,
    }
