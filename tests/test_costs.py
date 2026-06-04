from decimal import Decimal

from app.core.costs import estimate_cost_usd


def test_estimate_cost_usd():
    cost = estimate_cost_usd(
        input_tokens=1_000,
        output_tokens=500,
        input_cost_per_1m_tokens=2.0,
        output_cost_per_1m_tokens=10.0,
    )

    assert cost == Decimal("0.007000")
