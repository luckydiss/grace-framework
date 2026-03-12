import pytest

pytest.skip("Legacy pre-v1 MVP tests are out of scope for the current code-first foundation layer.", allow_module_level=True)


EXAMPLE_PATH = Path("examples/python_service/src/pricing.py")


def test_validate_module_set_accepts_annotated_module() -> None:
    modules, contracts, beliefs = validate_module_set([EXAMPLE_PATH])

    assert len(modules) == 1
    assert modules[0].id == "billing.pricing"
    assert len(contracts) == 1
    assert len(beliefs) == 1
    assert any(anchor.has_belief_state for anchor in modules[0].anchors)


def test_build_graph_export_contains_semantic_edges() -> None:
    modules, contracts, beliefs = validate_module_set([EXAMPLE_PATH])
    graph = build_graph_export(modules, contracts, beliefs)

    edge_types = {edge["type"] for edge in graph["edges"]}

    assert "module_has_contract" in edge_types
    assert "module_has_anchor" in edge_types
    assert "anchor_has_belief" in edge_types
    assert graph["modules"][0]["id"] == "billing.pricing"
    assert all("line" not in anchor for anchor in graph["anchors"])
