// @grace.module demo.parity
// @grace.purpose Verify semantic parity for the pilot Go adapter.
// @grace.interfaces example() int; load_example() int; ExampleService.run() int
// @grace.invariant Parity fixtures must keep the same semantic structure across language adapters.
// @grace.invariant Anchor ids remain stable so parity comparisons stay deterministic.

// @grace.anchor demo.parity.example
// @grace.complexity 1
func example() int {
	return 1
}

// @grace.anchor demo.parity.load_example
// @grace.complexity 6
// @grace.belief Go lacks async functions, so parity focuses on anchor shape, links, and deterministic spans instead of async runtime semantics.
// @grace.links demo.parity.example
func load_example() int {
	return example()
}

// @grace.anchor demo.parity.ExampleService
// @grace.complexity 2
type ExampleService struct {
}

// @grace.anchor demo.parity.ExampleService.run
// @grace.complexity 1
// @grace.links demo.parity.example
func (service ExampleService) run() int {
	return example()
}
