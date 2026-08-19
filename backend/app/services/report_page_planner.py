"""Deterministic editorial page planning shared by preview and PDF rendering."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any


class PageRecipe(StrEnum):
    COVER_HERO = "COVER_HERO"
    EXECUTIVE_OVERVIEW = "EXECUTIVE_OVERVIEW"
    OPERATIONS_SUMMARY = "OPERATIONS_SUMMARY"
    ENVIRONMENTAL_OVERVIEW = "ENVIRONMENTAL_OVERVIEW"
    BIKE_ZONE_FEATURE = "BIKE_ZONE_FEATURE"
    WASTE_FEATURE = "WASTE_FEATURE"
    CARBON_FEATURE = "CARBON_FEATURE"
    FORMS_INSIGHTS = "FORMS_INSIGHTS"
    PHOTO_STORY = "PHOTO_STORY"
    EDITORIAL_CLOSE = "EDITORIAL_CLOSE"
    MIXED_KPI_PAGE = "MIXED_KPI_PAGE"
    ENVIRONMENTAL_MANAGEMENT = "ENVIRONMENTAL_MANAGEMENT"
    CARBON_EQUIVALENCES = "CARBON_EQUIVALENCES"


class EditorialDensity(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


@dataclass(frozen=True)
class ReportPagePlan:
    number: int
    recipe: PageRecipe
    density: EditorialDensity
    title: str
    section_keys: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["recipe"] = self.recipe.value
        value["density"] = self.density.value
        value["section_keys"] = list(self.section_keys)
        return value


FEATURE_RECIPES = {
    "BIKE_ZONE": PageRecipe.BIKE_ZONE_FEATURE,
    "WASTE": PageRecipe.WASTE_FEATURE,
    "CARBON": PageRecipe.CARBON_FEATURE,
    "ENVIRONMENTAL_IMPACT": PageRecipe.ENVIRONMENTAL_OVERVIEW,
    "FORMS": PageRecipe.FORMS_INSIGHTS,
    "EVIDENCES": PageRecipe.PHOTO_STORY,
}
OPERATIONS = {"OPERATIONS", "STAFF", "TASKS", "INCIDENTS"}
CLOSE = {"RECOMMENDATIONS", "CONCLUSION"}


def section_density(section: dict[str, Any]) -> EditorialDensity:
    content = section.get("content") or {}
    score = len(content.get("fields") or []) + min(len(content.get("items") or []), 8)
    score += 3 if content.get("text") else 0
    if score <= 3:
        return EditorialDensity.LOW
    if score <= 10:
        return EditorialDensity.MEDIUM
    return EditorialDensity.HIGH


def visible_section(section: dict[str, Any]) -> dict[str, Any]:
    """Return renderable content while preserving the stored visibility choices."""
    content = section.get("content") or {}
    items = []
    for item in content.get("items") or []:
        if item.get("_is_visible", True) is False:
            continue
        items.append({key: value for key, value in item.items() if key != "_is_visible"})
    return {
        **section,
        "content": {
            **content,
            "fields": [
                field for field in content.get("fields") or [] if field.get("is_visible", True)
            ],
            "items": items,
        },
    }


def _page_density(sections: list[dict[str, Any]]) -> EditorialDensity:
    weights = {EditorialDensity.LOW: 1, EditorialDensity.MEDIUM: 2, EditorialDensity.HIGH: 3}
    score = sum(weights[section_density(section)] for section in sections)
    return (
        EditorialDensity.LOW
        if score <= 2
        else EditorialDensity.MEDIUM
        if score <= 5
        else EditorialDensity.HIGH
    )


def plan_pages(
    sections: list[dict[str, Any]], template: str, config: dict[str, Any] | None = None
) -> list[ReportPagePlan]:
    """Plan visible content without persisting derived pagination."""
    config = config or {}
    overrides = config.get("page_overrides") or {}
    visible = [
        visible_section(section)
        for section in sections
        if section.get("is_enabled") and section.get("section_type") != "COVER"
    ]
    pages: list[tuple[PageRecipe, list[dict[str, Any]]]] = []

    def take(types: set[str]) -> list[dict[str, Any]]:
        found = [s for s in visible if s.get("section_type") in types]
        for item in found:
            visible.remove(item)
        return found

    summary = take({"EXECUTIVE_SUMMARY", "EVENT_INFO", "SHOW_INFO"})
    if summary:
        executive = [item for item in summary if item.get("section_type") == "EXECUTIVE_SUMMARY"]
        facts = [item for item in summary if item not in executive]
        combined_fields = sum(
            len((item.get("content") or {}).get("fields") or []) for item in summary
        )
        if executive and facts and combined_fields > 8:
            pages.append((PageRecipe.EXECUTIVE_OVERVIEW, executive))
            pages.append((PageRecipe.MIXED_KPI_PAGE, facts))
        else:
            pages.append((PageRecipe.EXECUTIVE_OVERVIEW, summary))
    operations = take(OPERATIONS)
    if operations:
        pages.append((PageRecipe.OPERATIONS_SUMMARY, operations))

    if template == "ENVIRONMENTAL_STORY":
        management = take({"WASTE", "BIKE_ZONE"})
        if management:
            pages.append((PageRecipe.ENVIRONMENTAL_MANAGEMENT, management))
        footprint = take({"CARBON"})
        equivalences = [
            section
            for section in visible
            if section.get("section_key") == "preset_eco_equivalences"
        ]
        for section in equivalences:
            visible.remove(section)
        footprint.extend(equivalences)
        if footprint:
            pages.append((PageRecipe.CARBON_EQUIVALENCES, footprint))

    order = {
        "ENVIRONMENTAL_PREMIUM": ["ENVIRONMENTAL_IMPACT", "WASTE", "CARBON", "BIKE_ZONE", "EVIDENCES"],
        "ENVIRONMENTAL_STORY": ["ENVIRONMENTAL_IMPACT", "EVIDENCES", "FORMS"],
        "BIKE_ZONE": ["BIKE_ZONE", "FORMS", "EVIDENCES"],
        "OPERATIONS": ["FORMS", "EVIDENCES"],
        "EXECUTIVE": ["ENVIRONMENTAL_IMPACT", "WASTE", "CARBON", "BIKE_ZONE", "FORMS", "EVIDENCES"],
        "COMPLETE": ["ENVIRONMENTAL_IMPACT", "WASTE", "CARBON", "BIKE_ZONE", "FORMS", "EVIDENCES"],
    }.get(template, [])
    rank = {kind: index for index, kind in enumerate(order)}
    visible.sort(key=lambda s: (rank.get(s.get("section_type"), len(rank)), s.get("sort_order", 0)))

    pending: list[dict[str, Any]] = []
    for section in list(visible):
        override = overrides.get(section.get("section_key"), {})
        mode = override.get("mode", "AUTO")
        recipe = FEATURE_RECIPES.get(section.get("section_type"))
        own = mode in {"OWN_PAGE", "NEW_PAGE"} or (
            recipe and section_density(section) != EditorialDensity.LOW
        )
        if own:
            if pending:
                pages.append((PageRecipe.MIXED_KPI_PAGE, pending))
                pending = []
            pages.append((recipe or PageRecipe.MIXED_KPI_PAGE, [section]))
        else:
            pending.append(section)
            if len(pending) == (4 if template == "EXECUTIVE" else 3):
                pages.append((PageRecipe.MIXED_KPI_PAGE, pending))
                pending = []
    if pending:
        pages.append((PageRecipe.MIXED_KPI_PAGE, pending))

    close_sections: list[dict[str, Any]] = []
    kept = []
    for recipe, items in pages:
        closing = [item for item in items if item.get("section_type") in CLOSE]
        close_sections.extend(closing)
        rest = [item for item in items if item not in closing]
        if rest:
            kept.append((recipe, rest))
    pages = kept
    if close_sections:
        pages.append((PageRecipe.EDITORIAL_CLOSE, close_sections))

    # Explicit GROUP_WITH and KEEP_WITH_NEXT merge pages, while retaining a deterministic recipe.
    by_key = {s.get("section_key"): s for _, items in pages for s in items}
    for key, override in overrides.items():
        if override.get("mode") != "GROUP_WITH" or key not in by_key:
            continue
        target = override.get("group_with")
        source_index = next((i for i, (_, items) in enumerate(pages) if by_key[key] in items), None)
        target_index = next(
            (i for i, (_, items) in enumerate(pages) if by_key.get(target) in items), None
        )
        if source_index is not None and target_index is not None and source_index != target_index:
            moved = pages[source_index][1]
            pages[target_index][1].extend(moved)
            pages.pop(source_index)

    result = []
    for index, (recipe, items) in enumerate(pages, start=2):
        result.append(
            ReportPagePlan(
                index,
                recipe,
                _page_density(items),
                items[0]["title"],
                tuple(item["section_key"] for item in items),
            )
        )
    return [
        ReportPagePlan(1, PageRecipe.COVER_HERO, EditorialDensity.HIGH, "Portada", ("cover",)),
        *result,
    ]
