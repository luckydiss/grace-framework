// @grace.module demo.parity.async_shape
// @grace.purpose Verify async-shape semantic parity for the pilot Go adapter.
// @grace.interfaces fetch_example() int
// @grace.invariant Async-shape parity fixtures must keep anchor ids and complexity aligned across adapters.
// @grace.invariant Go uses a regular function equivalent while preserving the same semantic coordinates.

// @grace.anchor demo.parity.async_shape.fetch_example
// @grace.complexity 6
// @grace.belief Go has no async function syntax in this pilot, so parity is expressed through the same anchor and complexity on a regular function.
func fetch_example() int {
	return 1
}
