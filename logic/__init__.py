"""Paquete de lógica de negocio para la app."""

from .calculos import (
    calcular_mes,
    historico_anual,
    _ahorro_total_acumulado,
    _ocio_total_acumulado,
)

__all__ = [
    "calcular_mes",
    "historico_anual",
    "_ahorro_total_acumulado",
    "_ocio_total_acumulado",
]
