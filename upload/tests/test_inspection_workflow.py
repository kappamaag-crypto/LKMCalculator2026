from app.domain.inspection import InspectionDefect, InspectionMeasurement
from app.services.inspection_service import InspectionService


def test_inspection_record_preserves_unknown_acceptance():
    record = InspectionService.create_record(
        "I-001",
        object_name="Object",
        measurements=[InspectionMeasurement("DFT", 180, "um", point="P1")],
        defects=[InspectionDefect("Pinholes", severity="MINOR", location="Zone A")],
    )
    assert record.acceptance_status == "UNKNOWN"
    assert record.has_observations
    assert "UNKNOWN" in InspectionService.summary(record)


def test_inspection_rejects_invalid_status():
    try:
        InspectionService.create_record("I-002", acceptance_status="NOT_A_STATUS")
    except ValueError as exc:
        assert "статус" in str(exc).lower()
    else:
        raise AssertionError("invalid inspection status was accepted")
