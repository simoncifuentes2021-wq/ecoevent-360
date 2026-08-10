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
        PageRecipe.COVER_HERO,
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
    assert len(pages) == 2
    assert set(pages[1].section_keys) == {"waste", "carbon"}


def test_dense_event_facts_do_not_overflow_executive_overview():
    pages = plan_pages(
        [
            section("executive_summary", "EXECUTIVE_SUMMARY", 4),
            section("event_info", "EVENT_INFO", 9),
        ],
        "ENVIRONMENTAL_PREMIUM",
    )
    assert pages[1].section_keys == ("executive_summary",)
    assert pages[2].section_keys == ("event_info",)


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
        PageRecipe.COVER_HERO,
        PageRecipe.ENVIRONMENTAL_MANAGEMENT,
        PageRecipe.CARBON_EQUIVALENCES,
    ]
    assert pages[1].section_keys == ("waste", "bike_zone")
    assert pages[2].section_keys == ("carbon", "preset_eco_equivalences")
