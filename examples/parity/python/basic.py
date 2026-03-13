# @grace.module demo.parity
# @grace.purpose Verify semantic parity for the reference Python adapter.
# @grace.interfaces example() -> int; load_example() -> int; ExampleService.run() -> int
# @grace.invariant Parity fixtures must keep the same semantic structure across language adapters.
# @grace.invariant Anchor ids remain stable so parity comparisons stay deterministic.

# @grace.anchor demo.parity.example
# @grace.complexity 1
def example() -> int:
    return 1


# @grace.anchor demo.parity.load_example
# @grace.complexity 6
# @grace.belief Async parity fixture remains intentionally trivial so adapter comparison focuses on structure rather than domain logic.
# @grace.links demo.parity.example
async def load_example() -> int:
    return example()


# @grace.anchor demo.parity.ExampleService
# @grace.complexity 2
class ExampleService:
    # @grace.anchor demo.parity.ExampleService.run
    # @grace.complexity 1
    # @grace.links demo.parity.example
    def run(self) -> int:
        return example()
