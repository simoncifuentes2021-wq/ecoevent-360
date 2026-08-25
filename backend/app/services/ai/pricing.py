import json
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class ModelPricing:
    input_per_million: Decimal
    cached_input_per_million: Decimal
    output_per_million: Decimal

    def cost(self, input_tokens: int, output_tokens: int, cached_input_tokens: int = 0) -> Decimal:
        regular = max(0, input_tokens - cached_input_tokens)
        return (
            Decimal(regular) * self.input_per_million
            + Decimal(cached_input_tokens) * self.cached_input_per_million
            + Decimal(output_tokens) * self.output_per_million
        ) / Decimal(1_000_000)


class PricingRegistry:
    """Single pricing registry; local JSON may override the documented defaults."""

    def __init__(self, raw_json: str | None = None):
        self._prices: dict[str, ModelPricing] = {
            "openai:gpt-5.6-luna": ModelPricing(Decimal("0.20"), Decimal("0.02"), Decimal("1.20")),
        }
        if raw_json:
            for key, value in json.loads(raw_json).items():
                self._prices[key.lower()] = ModelPricing(
                    Decimal(str(value["input"])),
                    Decimal(str(value.get("cached_input", value["input"]))),
                    Decimal(str(value["output"])),
                )

    def get(self, provider: str, model: str) -> ModelPricing | None:
        return self._prices.get(f"{provider}:{model}".lower())
