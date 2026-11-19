"""Enrutador de vistas y exportación CSV del header ("Exportar reporte")."""

from __future__ import annotations

from typing import Any

import pandas as pd

from services.backend_bridge import generar_tabla_franjas_detalle


MODULOS = {
    "Resumen operativo": "pages_resumen",
    "Pronóstico de demanda": "pages_pronostico",
    "Recomendaciones de inventario": "pages_recomendaciones",
    "Análisis histórico": "pages_historico",
    "Estado de datos y modelo": "pages_estado",
    "Propósito e Incorporación": "pages_proposito",
}


def render(pagina: str, state: dict[str, Any]) -> None:
    import importlib

    modulo = importlib.import_module(f"ui.{MODULOS.get(pagina, 'pages_resumen')}")
    modulo.render(state)


def export_csv(pagina: str, state: dict[str, Any]) -> bytes | None:
    """CSV del header: desglose por categoría (y por franja en Pronóstico) del escenario activo."""
    if pagina == "Propósito e Incorporación":
        return None
    resumen = state["store_summary"]
    if pagina == "Pronóstico de demanda":
        df = generar_tabla_franjas_detalle(state["store_location"], state["fecha_str"], resumen["desglose"])
    else:
        df = pd.DataFrame(
            [
                {
                    "sucursal": d["sucursal"],
                    "fecha": d["fecha"],
                    "categoria": d["categoria"],
                    "unidades_estimadas": d["unidades_estimadas"],
                    "unidades_recomendadas": d["unidades_recomendadas"],
                    "rango_85_min": d["rango_estimado_85"][0],
                    "rango_85_max": d["rango_estimado_85"][1],
                    "ref_historica_dow": d["ref_historica_dow"],
                    "variacion_pct": d["delta_pct_vs_ref"],
                    "nivel_demanda": d["nivel_demanda"],
                }
                for d in resumen["desglose"]
            ]
        )
    return df.to_csv(index=False).encode("utf-8")
