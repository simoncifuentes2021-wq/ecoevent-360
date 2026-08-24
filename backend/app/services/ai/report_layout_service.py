from typing import Literal
from pydantic import BaseModel, Field, model_validator
from app.services.report_data_binding_registry import REGISTRY

ALLOWED_TYPES = {"TITLE", "TEXT", "KPI", "IMAGE", "CHART", "SHAPE"}
ALLOWED_FONTS = {"Arial", "Helvetica", "Inter", "Georgia"}


class AIElementPlan(BaseModel):
    type: Literal["TITLE", "TEXT", "KPI", "IMAGE", "CHART", "SHAPE"]
    x: float = Field(ge=0)
    y: float = Field(ge=0)
    width: float = Field(ge=24, le=1000)
    height: float = Field(ge=24, le=1414)
    content: dict = Field(default_factory=dict)
    style: dict = Field(default_factory=dict)
    data_binding: dict | None = None


class AIPagePlanSchema(BaseModel):
    width: float = 1000
    height: float = 1414
    elements: list[AIElementPlan] = Field(max_length=30)

    @model_validator(mode="after")
    def validate_layout(self):
        for item in self.elements:
            if item.x + item.width > self.width or item.y + item.height > self.height:
                raise ValueError("AI element exceeds page bounds")
            font = item.style.get("fontFamily", "Arial")
            if font not in ALLOWED_FONTS:
                raise ValueError("AI selected a forbidden font")
            if item.data_binding and item.data_binding.get("key") not in REGISTRY:
                raise ValueError("AI selected an unknown binding")
        return self


class LayoutValidator:
    @staticmethod
    def validate(raw: dict) -> AIPagePlanSchema:
        plan = AIPagePlanSchema.model_validate(raw)
        severe = 0
        for index, first in enumerate(plan.elements):
            for second in plan.elements[index + 1 :]:
                overlap = max(
                    0, min(first.x + first.width, second.x + second.width) - max(first.x, second.x)
                ) * max(
                    0,
                    min(first.y + first.height, second.y + second.height) - max(first.y, second.y),
                )
                if overlap > min(first.width * first.height, second.width * second.height) * 0.6:
                    severe += 1
        if severe:
            raise ValueError("AI page contains severe overlaps")
        return plan
