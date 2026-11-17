#!/usr/bin/env python3
"""Example 6: Metric calculation, registry exploration, and multi-day aggregation."""

from __future__ import annotations

from metametrics import Metric, MetricCalculator, MetricRegistry


def main() -> None:
    registry = MetricRegistry()
    print("Available Metrics in Catalogue:")
    for metric in Metric:
        definition = registry.definition(metric)
        kind = "Derived" if definition.is_derived else "Foundational"
        print(f"  - {metric.value:20} [{kind:12}] Unit: {definition.unit.value}")

    calculator = MetricCalculator()
    values = {
        Metric.SPEND.value: 120.0,
        Metric.CLICKS.value: 80.0,
        Metric.PURCHASE_VALUE.value: 480.0,
        Metric.IMPRESSIONS.value: 4000.0,
    }
    roas = calculator.calculate(Metric.ROAS, values)
    cpc = calculator.calculate(Metric.CPC, values)
    ctr = calculator.calculate(Metric.CTR, values)
    cpm = calculator.calculate(Metric.CPM, values)

    print("\nCalculated Derived Metrics:")
    print(f"  ROAS: {roas:.2f}x")
    print(f"  CPC:  ${cpc:.2f}")
    print(f"  CTR:  {ctr:.2f}%")
    print(f"  CPM:  ${cpm:.2f}")


if __name__ == "__main__":
    main()
