"""Custom PC embodied carbon accounting using explicit BOM matching and optional proxies."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np


class CustomPcValidationError(ValueError):
    """Raised when a custom PC BOM is invalid or a proxy cross-matches types."""


@dataclass(frozen=True)
class BuildComponent:
    component_id: str
    component_type: str
    quantity: int = 1
    proxy_component_id: str | None = None

    def __post_init__(self) -> None:
        if not self.component_id:
            raise CustomPcValidationError("component_id is required")
        if not self.component_type:
            raise CustomPcValidationError("component_type is required")
        if not isinstance(self.quantity, int) or self.quantity <= 0:
            raise CustomPcValidationError("quantity must be a positive integer")


@dataclass(frozen=True)
class ComponentFactor:
    component_id: str
    component_type: str
    label: str
    kg_co2e: float
    source: str
    lifecycle_boundary: str

    def __post_init__(self) -> None:
        if not self.component_id:
            raise CustomPcValidationError("component_id is required")
        if not self.component_type:
            raise CustomPcValidationError("component_type is required")
        if not np.isfinite(float(self.kg_co2e)) or float(self.kg_co2e) < 0:
            raise CustomPcValidationError("kg_co2e must be finite and non-negative")


@dataclass(frozen=True)
class CustomPcComponentResult:
    component_id: str
    component_type: str
    quantity: int
    status: str
    kg_co2e: float | None
    method: str
    factor_source: str | None = None
    factor_id: str | None = None


@dataclass(frozen=True)
class CustomPcResult:
    complete: bool
    total_kg_co2e: float | None
    resolved_subtotal_kg_co2e: float
    components: list[CustomPcComponentResult]


def calculate_custom_pc_embodied_carbon(
    build_components: Iterable[BuildComponent],
    factors: Iterable[ComponentFactor],
) -> CustomPcResult:
    """Resolve a custom PC BOM against validated embodied-carbon factors.

    Each build component resolves either to a direct factor match or an explicit proxy of the same
    component type. Missing component factors leave the assembly incomplete and the component status
    is marked as "unresolved".
    """
    factor_by_id = {factor.component_id: factor for factor in factors}
    component_results: list[CustomPcComponentResult] = []
    resolved_total = 0.0

    for component in build_components:
        match = factor_by_id.get(component.component_id)
        chosen_factor = None
        method = "missing_factor"
        status = "unresolved"
        value = 0.0

        if component.proxy_component_id is not None:
            proxy_factor = factor_by_id.get(component.proxy_component_id)
            if proxy_factor is None:
                raise CustomPcValidationError(f"Proxy factor '{component.proxy_component_id}' was not found")
            if proxy_factor.component_type != component.component_type:
                raise CustomPcValidationError("Proxy component type must match the requested component type")
            chosen_factor = proxy_factor
            method = "explicit_proxy_factor"
            status = "resolved"
            value = chosen_factor.kg_co2e * component.quantity
            resolved_total += value
        elif match is not None:
            chosen_factor = match
            if chosen_factor.component_type != component.component_type:
                raise CustomPcValidationError("Factor type must match the requested component type")
            method = "direct_factor"
            status = "resolved"
            value = chosen_factor.kg_co2e * component.quantity
            resolved_total += value

        component_results.append(
            CustomPcComponentResult(
                component_id=component.component_id,
                component_type=component.component_type,
                quantity=component.quantity,
                status=status,
                kg_co2e=value if status == "resolved" else None,
                method=method,
                factor_source=chosen_factor.source if chosen_factor is not None else None,
                factor_id=chosen_factor.component_id if chosen_factor is not None else None,
            )
        )

    complete = all(item.status == "resolved" for item in component_results)
    total_kg_co2e = resolved_total if complete else None
    return CustomPcResult(
        complete=complete,
        total_kg_co2e=total_kg_co2e,
        resolved_subtotal_kg_co2e=resolved_total,
        components=component_results,
    )
