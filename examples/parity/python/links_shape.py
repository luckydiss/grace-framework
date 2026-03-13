# @grace.module demo.parity.links_shape
# @grace.purpose Verify linked semantic block ordering for the reference Python adapter.
# @grace.interfaces seed() -> int; transform() -> int; publish() -> int
# @grace.invariant Link-shape fixtures must preserve anchor order and link edges across adapters.
# @grace.invariant Deterministic block ordering is part of the parity surface.

# @grace.anchor demo.parity.links_shape.seed
# @grace.complexity 1
def seed() -> int:
    return 1


# @grace.anchor demo.parity.links_shape.transform
# @grace.complexity 2
# @grace.links demo.parity.links_shape.seed
def transform() -> int:
    return seed() + 1


# @grace.anchor demo.parity.links_shape.publish
# @grace.complexity 2
# @grace.links demo.parity.links_shape.transform
def publish() -> int:
    return transform()
