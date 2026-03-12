# @grace.module billing.pricing
# @grace.purpose Determine discount strategy and apply discounts.
# @grace.interfaces apply_discount(price:int, percent:int) -> int; choose_discount_strategy(customer_tier:str, cart_total:int) -> int
# @grace.invariant Discount percent must never be negative.
# @grace.invariant Anchor ids remain stable unless pricing semantics change.

# @grace.anchor billing.pricing.apply_discount
# @grace.complexity 2
def apply_discount(price: int, percent: int) -> int:
    return price - ((price * percent) // 100)


# @grace.anchor billing.pricing.choose_discount_strategy
# @grace.complexity 6
# @grace.belief VIP tier is the dominant pricing signal and threshold rules remain deterministic for the MVP.
# @grace.links billing.pricing.apply_discount
def choose_discount_strategy(customer_tier: str, cart_total: int) -> int:
    if customer_tier == "vip" and cart_total >= 1000:
        return 20
    if customer_tier == "vip":
        return 15
    if cart_total >= 500:
        return 10
    return 0
