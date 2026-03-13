# @grace.module demo.parity.async_shape
# @grace.purpose Verify async-shape semantic parity for the reference Python adapter.
# @grace.interfaces fetch_example() -> int
# @grace.invariant Async-shape parity fixtures must keep anchor ids and complexity aligned across adapters.
# @grace.invariant Go may use a regular function equivalent while preserving the same semantic coordinates.

# @grace.anchor demo.parity.async_shape.fetch_example
# @grace.complexity 6
# @grace.belief Async parity should stay structurally trivial so cross-language comparison focuses on anchor semantics rather than runtime behavior.
async def fetch_example() -> int:
    return 1
