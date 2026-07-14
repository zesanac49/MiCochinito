"""Paginación estándar (doc 07 §1): envelope items/total/page/size."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")

SIZE_MAX = 100


@dataclass(frozen=True, slots=True)
class ParametrosPagina:
    page: int = 1
    size: int = 25

    def __post_init__(self) -> None:
        if self.page < 1:
            raise ValueError("page debe ser >= 1")
        if not (1 <= self.size <= SIZE_MAX):
            raise ValueError(f"size debe estar entre 1 y {SIZE_MAX}")

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.size


@dataclass(frozen=True, slots=True)
class Pagina(Generic[T]):
    items: list[T]
    total: int
    page: int
    size: int
