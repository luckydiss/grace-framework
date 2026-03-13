// @grace.module demo.parity.links_shape
// @grace.purpose Verify linked semantic block ordering for the pilot Go adapter.
// @grace.interfaces seed() int; transform() int; publish() int
// @grace.invariant Link-shape fixtures must preserve anchor order and link edges across adapters.
// @grace.invariant Deterministic block ordering is part of the parity surface.

// @grace.anchor demo.parity.links_shape.seed
// @grace.complexity 1
func seed() int {
	return 1
}

// @grace.anchor demo.parity.links_shape.transform
// @grace.complexity 2
// @grace.links demo.parity.links_shape.seed
func transform() int {
	return seed() + 1
}

// @grace.anchor demo.parity.links_shape.publish
// @grace.complexity 2
// @grace.links demo.parity.links_shape.transform
func publish() int {
	return transform()
}
