# @grace.module demo.parity.service_shape
# @grace.purpose Verify class-and-method semantic parity for the reference Python adapter.
# @grace.interfaces ExampleService.run() -> int
# @grace.invariant Service-shape parity fixtures must preserve class and method anchors across adapters.
# @grace.invariant Method links should stay deterministic across language adapters.

# @grace.anchor demo.parity.service_shape.ExampleService
# @grace.complexity 2
class ExampleService:
    # @grace.anchor demo.parity.service_shape.ExampleService.run
    # @grace.complexity 1
    def run(self) -> int:
        return 1
