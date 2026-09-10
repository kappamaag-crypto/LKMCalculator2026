"""Commercial packaging planning, kept separate from engineering calculation."""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil
from typing import Iterable

from .models import Package


@dataclass(frozen=True)
class PackagingPlan:
    """Purchase requirement for one package option."""

    package: Package
    required_quantity: float
    reserve_percent: float
    quantity_to_purchase: float
    purchase_units: int
    estimated_material_cost: float | None


class PackagingPlanner:
    """Translate an already calculated requirement into package units.

    This is a commercial purchasing aid only. It does not model warehouse stock,
    stock balances, inventory reservations, or procurement orders, and it never
    changes the engineering calculation result.
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
        """Return the minimum whole package count covering requirement + reserve."""
        if required_quantity < 0:
            raise ValueError("required_quantity must be non-negative")
        if reserve_percent < 0:
            raise ValueError("reserve_percent must be non-negative")

        package_quantity = cls._package_quantity(package)
        quantity_to_purchase = required_quantity * (1.0 + reserve_percent / 100.0)
        purchase_units = ceil(quantity_to_purchase / package_quantity)

        estimated_cost = None
        if unit_price is not None:
            if unit_price < 0:
                raise ValueError("unit_price must be non-negative")
            estimated_cost = purchase_units * unit_price

        return PackagingPlan(
            package=package,
            required_quantity=required_quantity,
            reserve_percent=reserve_percent,
            quantity_to_purchase=quantity_to_purchase,
            purchase_units=purchase_units,
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
        """Build independent purchasable package options without inventory logic."""
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

        return sorted(plans, key=lambda item: (item.purchase_units, item.quantity_to_purchase))
