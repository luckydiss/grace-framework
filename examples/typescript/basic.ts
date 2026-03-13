// @grace.module billing.pricing
// @grace.purpose Determine discount behavior in a TypeScript pilot module.
// @grace.interfaces applyDiscount(price:number, percent:number): number; chooseDiscount(customerTier:string): Promise<number>
// @grace.invariant Discount percent must never be negative.
// @grace.invariant Anchor ids remain stable unless pricing semantics change.

// @grace.anchor billing.pricing.applyDiscount
// @grace.complexity 2
function applyDiscount(price: number, percent: number): number {
  return price - Math.floor((price * percent) / 100);
}

/* @grace.anchor billing.pricing.chooseDiscount */
/* @grace.complexity 6 */
/* @grace.belief VIP remains the dominant signal in the TypeScript pilot adapter. */
/* @grace.links billing.pricing.applyDiscount */
async function chooseDiscount(customerTier: string): Promise<number> {
  return customerTier === "vip" ? 15 : 0;
}

// @grace.anchor billing.pricing.StrategyRegistry
// @grace.complexity 2
class StrategyRegistry {
  // @grace.anchor billing.pricing.StrategyRegistry.resolve
  // @grace.complexity 1
  resolve(): number {
    return 0;
  }
}
