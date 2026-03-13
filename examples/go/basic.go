// @grace.module demo.go_basic
// @grace.purpose Demonstrate the minimal Go pilot adapter for GRACE.
// @grace.interfaces example() int; ExampleService.run() int
// @grace.invariant The Go example should stay intentionally small and deterministic.
// @grace.invariant Anchor ids remain stable unless the example semantics change.

// @grace.anchor demo.go_basic.example
// @grace.complexity 1
func example() int {
	return 1
}

// @grace.anchor demo.go_basic.ExampleService
// @grace.complexity 2
type ExampleService struct {
}

// @grace.anchor demo.go_basic.ExampleService.run
// @grace.complexity 1
// @grace.links demo.go_basic.example
func (service ExampleService) run() int {
	return example()
}
