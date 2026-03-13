// @grace.module demo.parity
// @grace.purpose Verify semantic parity for the pilot TypeScript adapter.
// @grace.interfaces example(): number; load_example(): Promise<number>; ExampleService.run(): number
// @grace.invariant Parity fixtures must keep the same semantic structure across language adapters.
// @grace.invariant Anchor ids remain stable so parity comparisons stay deterministic.

// @grace.anchor demo.parity.example
// @grace.complexity 1
function example(): number {
  return 1;
}

/* @grace.anchor demo.parity.load_example */
/* @grace.complexity 6 */
/* @grace.belief Async parity fixture remains intentionally trivial so adapter comparison focuses on structure rather than domain logic. */
/* @grace.links demo.parity.example */
async function load_example(): Promise<number> {
  return example();
}

// @grace.anchor demo.parity.ExampleService
// @grace.complexity 2
class ExampleService {
  // @grace.anchor demo.parity.ExampleService.run
  // @grace.complexity 1
  // @grace.links demo.parity.example
  run(): number {
    return example();
  }
}
