"""Commercial packaging and procurement calculations.

This module deliberately does not alter engineering consumption. It converts an
already calculated requirement into purchasable package units and exposes the
result as a separate commercial value object.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil
from typing import Iterable

from .models import Package


@dataclass(frozen=True)
class PackagingPlan:
    """Purchase plan for one package option."""

    package: Package
    required_quantity: float
    reserve_percent: float
    quantity_with_reserve: float
    purchase_units: int
    purchased_quantity: float
    remainder_quantity: float
    estimated_material_cost: float | None


class PackagingPlanner:
    """Translate an engineering requirement into package quantities.

    The planner is intentionally separate from the calculation engine. It never
    changes DFT, consumption, losses, or any other engineering result.
    """

    @staticmethod
    def _package_quantity(package: Package) -> float:
        quantity = package.net_weight_kg
        if quantity is None:
            quantity = package.net_volume_l
        if quantity is None or quantity <= 0:
            raise ValueError("Package must have a positive net weight or volume")
        return float(quantity)

    @classmethod
    def plan(
        cls,
        required_quantity: float,
        package: Package,
        *,
        reserve_percent: float = 0.0,
        unit_price: float | None = None,
    ) -> PackagingPlan:
        """Return the minimum whole package count covering requirement + reserve.

        ``unit_price`` is the price of one physical package. When it is not
        supplied, the estimated purchase cost remains ``None`` rather than being
        inferred from an engineering consumption price.
        """
        if required_quantity < 0:
            raise ValueError("required_quantity must be non-negative")
        if reserve_percent < 0:
            raise ValueError("reserve_percent must be non-negative")

        package_quantity = cls._package_quantity(package)
        quantity_with_reserve = required_quantity * (1.0 + reserve_percent / 100.0)
        purchase_units = ceil(quantity_with_reserve / package_quantity)
        purchased_quantity = purchase_units * package_quantity
        remainder_quantity = purchased_quantity - required_quantity

        estimated_cost = None
        if unit_price is not None:
            if unit_price < 0:
                raise ValueError("unit_price must be non-negative")
            estimated_cost = purchase_units * unit_price

        return PackagingPlan(
            package=package,
            required_quantity=required_quantity,
            reserve_percent=reserve_percent,
            quantity_with_reserve=quantity_with_reserve,
            purchase_units=purchase_units,
            purchased_quantity=purchased_quantity,
            remainder_quantity=remainder_quantity,
            estimated_material_cost=estimated_cost,
        )

    @classmethod
    def plan_options(
        cls,
        required_quantity: float,
        packages: Iterable[Package],
        *,
        reserve_percent: float = 0.0,
        unit_prices: dict[int, float] | None = None,
    ) -> list[PackagingPlan]:
        """Build independent plans for all valid package options.

        Options are sorted by purchase units and then by remainder, making the
        smallest operational plan the first candidate without pretending that a
        global procurement optimisation has been performed.
        """
        prices = unit_prices or {}
        plans: list[PackagingPlan] = []
        for package in packages:
            try:
                plan = cls.plan(
                    required_quantity,
                    package,
                    reserve_percent=reserve_percent,
                    unit_price=prices.get(package.id) if package.id is not None else None,
                )
            except ValueError:
                continue
            plans.append(plan)

        return sorted(plans, key=lambda item: (item.purchase_units, item.remainder_quantity))
