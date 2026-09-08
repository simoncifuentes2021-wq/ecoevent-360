from app.services.report_page_planner import PageRecipe, plan_pages, section_density


def section(key, kind, fields=1, *, enabled=True, items=0):
    return {
        "section_key": key,
        "section_type": kind,
        "title": key.replace("_", " ").title(),
        "is_enabled": enabled,
        "sort_order": 1,
        "content": {"fields": [{}] * fields, "items": [{}] * items},
    }


def test_small_operations_are_grouped_on_one_page():
    pages = plan_pages(
        [section("staff", "STAFF"), section("tasks", "TASKS", 3), section("incidents", "INCIDENTS", 2)],
        "OPERATIONS",
    )
    operations = [page for page in pages if page.recipe == PageRecipe.OPERATIONS_SUMMARY]
    assert len(operations) == 1
    assert operations[0].section_keys == ("staff", "tasks", "incidents")


def test_large_waste_and_bike_photo_feature_get_own_pages():
    pages = plan_pages(
        [section("waste", "WASTE", 5, items=8), section("bike_zone", "BIKE_ZONE", 4)],
        "ENVIRONMENTAL_PREMIUM",
    )
    assert [page.recipe for page in pages] == [
        PageRecipe.WASTE_FEATURE,
        PageRecipe.BIKE_ZONE_FEATURE,
    ]
    assert section_density(section("waste", "WASTE", 5, items=8)).value == "HIGH"


def test_invisible_section_never_creates_page_and_own_page_override_works():
    pages = plan_pages(
        [section("forms", "FORMS", enabled=False), section("note", "CUSTOM")],
        "COMPLETE",
        {"mode": "CUSTOM", "page_overrides": {"note": {"mode": "OWN_PAGE"}}},
    )
    assert all("forms" not in page.section_keys for page in pages)
    assert pages[-1].section_keys == ("note",)


def test_group_with_override_combines_sections():
    pages = plan_pages(
        [section("waste", "WASTE", 5), section("carbon", "CARBON", 5)],
        "COMPLETE",
        {"page_overrides": {"carbon": {"mode": "GROUP_WITH", "group_with": "waste"}}},
    )
    assert len(pages) == 1
    assert set(pages[0].section_keys) == {"waste", "carbon"}


def test_dense_event_facts_do_not_overflow_executive_overview():
    pages = plan_pages(
        [
            section("executive_summary", "EXECUTIVE_SUMMARY", 4),
            section("event_info", "EVENT_INFO", 9),
        ],
        "ENVIRONMENTAL_PREMIUM",
    )
    assert pages[0].section_keys == ("executive_summary",)
    assert pages[1].section_keys == ("event_info",)


def test_executive_summary_page_modes_are_applied():
    sections = [
        section("executive_summary", "EXECUTIVE_SUMMARY", 2),
        section("event_info", "EVENT_INFO", 2),
        section("waste", "WASTE", 5),
    ]
    own = plan_pages(
        sections,
        "COMPLETE",
        {"page_overrides": {"executive_summary": {"mode": "OWN_PAGE"}}},
    )
    assert own[0].section_keys == ("executive_summary",)
    assert own[1].section_keys == ("event_info",)

    kept = plan_pages(
        sections,
        "COMPLETE",
        {"page_overrides": {"executive_summary": {"mode": "KEEP_WITH_NEXT"}}},
    )
    assert set(kept[0].section_keys) == {"executive_summary", "event_info", "waste"}


def test_environmental_story_builds_two_bounded_editorial_pages():
    pages = plan_pages(
        [
            section("waste", "WASTE", 2, items=6),
            section("bike_zone", "BIKE_ZONE", 3),
            section("carbon", "CARBON", 5),
            section("preset_eco_equivalences", "CUSTOM", 4),
        ],
        "ENVIRONMENTAL_STORY",
    )
    assert [page.recipe for page in pages] == [
        PageRecipe.ENVIRONMENTAL_MANAGEMENT,
        PageRecipe.CARBON_EQUIVALENCES,
    ]
    assert pages[0].section_keys == ("waste", "bike_zone")
    assert pages[1].section_keys == ("carbon", "preset_eco_equivalences")


def test_environmental_story_isolates_waste_when_bike_zone_is_disabled():
    pages = plan_pages(
        [
            section("waste", "WASTE", 2, items=6),
            section("bike_zone", "BIKE_ZONE", 3, enabled=False),
        ],
        "ENVIRONMENTAL_STORY",
        {"page_overrides": {"waste": {"mode": "OWN_PAGE"}}},
    )

    assert len(pages) == 1
    assert pages[0].recipe == PageRecipe.WASTE_FEATURE
    assert pages[0].section_keys == ("waste",)


def test_environmental_story_separates_management_sections_when_one_owns_a_page():
    pages = plan_pages(
        [
            section("waste", "WASTE", 2, items=6),
            section("bike_zone", "BIKE_ZONE", 3),
        ],
        "ENVIRONMENTAL_STORY",
        {"page_overrides": {"waste": {"mode": "OWN_PAGE"}}},
    )

    assert [page.recipe for page in pages] == [
        PageRecipe.WASTE_FEATURE,
        PageRecipe.BIKE_ZONE_FEATURE,
    ]
    assert pages[0].section_keys == ("waste",)
    assert pages[1].section_keys == ("bike_zone",)


def test_environmental_story_renders_standalone_ecoequivalences_without_carbon():
    eco = section("preset_eco_equivalences", "CUSTOM", 2)
    eco["layout_variant"] = "BIG_NUMBERS"

    pages = plan_pages(
        [section("carbon", "CARBON", 3, enabled=False), eco],
        "ENVIRONMENTAL_STORY",
    )

    assert len(pages) == 1
    assert pages[0].recipe == PageRecipe.CARBON_EQUIVALENCES
    assert pages[0].section_keys == ("preset_eco_equivalences",)


def test_environmental_story_separates_custom_ecoequivalence_composition_from_carbon():
    eco = section("preset_eco_equivalences", "CUSTOM", 2)
    eco["layout_variant"] = "PHOTO_GRID"

    pages = plan_pages(
        [section("carbon", "CARBON", 3), eco],
        "ENVIRONMENTAL_STORY",
    )

    assert [page.recipe for page in pages] == [
        PageRecipe.CARBON_FEATURE,
        PageRecipe.CARBON_EQUIVALENCES,
    ]
    assert pages[0].section_keys == ("carbon",)
    assert pages[1].section_keys == ("preset_eco_equivalences",)
