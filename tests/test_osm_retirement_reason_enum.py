from app.models.enum_models import OSMRetirementReasonEnum


def test_osm_retirement_reason_enum_accepts_legacy_oc_codes():
    assert OSMRetirementReasonEnum("OC1") is OSMRetirementReasonEnum.DIED
    assert OSMRetirementReasonEnum("OC2") is OSMRetirementReasonEnum.RESIGNED
    assert OSMRetirementReasonEnum("OC3") is OSMRetirementReasonEnum.MOVED_OR_ABSENT
    assert OSMRetirementReasonEnum("OC4") is OSMRetirementReasonEnum.SICK_OR_DISABLED
    assert (
        OSMRetirementReasonEnum("OC5")
        is OSMRetirementReasonEnum.NEVER_PARTICIPATED_IN_OSM_ACTIVITIES
    )
    assert (
        OSMRetirementReasonEnum("OC6") is OSMRetirementReasonEnum.COMMUNITY_REQUESTS_REMOVAL
    )
    assert (
        OSMRetirementReasonEnum("OC7")
        is OSMRetirementReasonEnum.BEHAVIOR_DAMAGING_REPUTATION
    )


def test_osm_retirement_reason_enum_unknown_falls_back():
    assert OSMRetirementReasonEnum("-") is OSMRetirementReasonEnum.UNKNOWN
    assert OSMRetirementReasonEnum("") is OSMRetirementReasonEnum.UNKNOWN
