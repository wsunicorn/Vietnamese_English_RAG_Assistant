from decimal import Decimal, ROUND_HALF_UP


def estimate_cost_usd(
    input_tokens: int,
    output_tokens: int,
    input_cost_per_1m_tokens: float,
    output_cost_per_1m_tokens: float,
) -> Decimal:
    input_cost = Decimal(input_tokens) * Decimal(str(input_cost_per_1m_tokens)) / Decimal(1_000_000)
    output_cost = Decimal(output_tokens) * Decimal(str(output_cost_per_1m_tokens)) / Decimal(1_000_000)
    return (input_cost + output_cost).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
