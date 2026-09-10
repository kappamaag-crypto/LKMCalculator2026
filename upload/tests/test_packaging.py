from app.domain.models import Package
from app.domain.packaging import PackagingPlanner


def test_packaging_ceil_and_requirement_stays_engineering_input():
    package = Package(id=1, material_id=10, package_name="20 kg", net_weight_kg=20)

    plan = PackagingPlanner.plan(43.0, package)

    assert plan.required_quantity == 43.0
    assert plan.quantity_to_purchase == 43.0
    assert plan.purchase_units == 3
    assert plan.estimated_material_cost is None


def test_packaging_reserve_is_commercial_only():
    package = Package(id=1, material_id=10, package_name="25 kg", net_weight_kg=25)

    plan = PackagingPlanner.plan(50.0, package, reserve_percent=10)

    assert plan.required_quantity == 50.0
    assert plan.quantity_to_purchase == 55.0
    assert plan.purchase_units == 3


def test_packaging_can_use_volume_when_weight_is_missing():
    package = Package(id=2, material_id=10, package_name="10 l", net_volume_l=10)

    plan = PackagingPlanner.plan(21.0, package, unit_price=1500.0)

    assert plan.purchase_units == 3
    assert plan.quantity_to_purchase == 21.0
    assert plan.estimated_material_cost == 4500.0


def test_plan_options_skips_invalid_packages_and_keeps_valid_options():
    packages = [
        Package(id=1, material_id=10, package_name="20 kg", net_weight_kg=20),
        Package(id=2, material_id=10, package_name="invalid"),
        Package(id=3, material_id=10, package_name="10 kg", net_weight_kg=10),
    ]

    plans = PackagingPlanner.plan_options(25.0, packages, unit_prices={1: 1000, 3: 600})

    assert [plan.package.id for plan in plans] == [1, 3]
    assert plans[0].purchase_units == 2
    assert plans[0].estimated_material_cost == 2000.0
    assert plans[1].purchase_units == 3
    assert plans[1].estimated_material_cost == 1800.0
