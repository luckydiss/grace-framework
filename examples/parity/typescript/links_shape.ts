// @grace.module demo.parity.links_shape
// @grace.purpose Verify linked semantic block ordering for the pilot TypeScript adapter.
// @grace.interfaces seed(): number; transform(): number; publish(): number
// @grace.invariant Link-shape fixtures must preserve anchor order and link edges across adapters.
// @grace.invariant Deterministic block ordering is part of the parity surface.

// @grace.anchor demo.parity.links_shape.seed
// @grace.complexity 1
function seed(): number {
  return 1;
}

// @grace.anchor demo.parity.links_shape.transform
// @grace.complexity 2
// @grace.links demo.parity.links_shape.seed
function transform(): number {
  return seed() + 1;
}

// @grace.anchor demo.parity.links_shape.publish
// @grace.complexity 2
// @grace.links demo.parity.links_shape.transform
function publish(): number {
  return transform();
}
