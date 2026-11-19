"""Enrutador de vistas y exportación CSV del header ("Exportar reporte").

Cada vista exporta el contenido que muestra (CSV UTF-8 con BOM para que Excel lea bien los acentos).
"""

from __future__ import annotations

import importlib
from typing import Any

import pandas as pd
import streamlit as st

from services.backend_bridge import (
    cargar_resultados_experimentos,
    generar_recomendaciones_turno,
    generar_tabla_franjas_detalle,
    load_transacciones,
    resumen_historico,
)

MODULOS = {
    "Resumen operativo": "pages_resumen",
    "Pronóstico de demanda": "pages_pronostico",
    "Recomendaciones de inventario": "pages_recomendaciones",
    "Análisis histórico": "pages_historico",
    "Estado de datos y modelo": "pages_estado",
    "Propósito e Incorporación": "pages_proposito",
}
FRANJAS_HIST = {"Todo el día (06:00 - 20:00)": (6, 20), "Turno Mañana (06:00 - 14:00)": (6, 13), "Turno Tarde (14:00 - 20:00)": (14, 20)}


def render(pagina: str, state: dict[str, Any]) -> None:
    modulo = importlib.import_module(f"ui.{MODULOS.get(pagina, 'pages_resumen')}")
    modulo.render(state)


def _csv(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8-sig")


def export_csv(pagina: str, state: dict[str, Any]) -> bytes | None:
    """CSV del botón 'Exportar reporte' según la vista activa."""
    if pagina == "Propósito e Incorporación":
        return None
    resumen = state["store_summary"]
    store, fecha = state["store_location"], state["fecha_str"]

    if pagina == "Pronóstico de demanda":
        return _csv(generar_tabla_franjas_detalle(store, fecha, resumen["desglose"]))

    if pagina == "Recomendaciones de inventario":
        recs = generar_recomendaciones_turno(store, fecha, resumen["desglose"])
        return _csv(pd.DataFrame([
            {"sucursal": r["sucursal"], "fecha": fecha, "producto": r["producto"], "categoria": r["categoria"],
             "participacion_en_categoria_pct": r["participacion_pct"], "demanda_estimada": r["demanda_num"],
             "margen_seguridad": r["margen_seguridad"], "cantidad_sugerida": r["cant_sugerida_num"],
             "motivo": r["motivo"], "prioridad": r["prioridad"]}
            for r in recs
        ]))

    if pagina == "Análisis histórico":
        tx = load_transacciones()
        por_defecto = (tx["fecha_dt"].min().date(), tx["fecha_dt"].max().date())
        rango = st.session_state.get("hist_rango") or por_defecto
        d_ini, d_fin = rango if isinstance(rango, (tuple, list)) and len(rango) == 2 else por_defecto
        suc = st.session_state.get("hist_store", "Todas las sucursales (3)")
        cat = st.session_state.get("hist_cat", "Todas las categorías")
        h_ini, h_fin = FRANJAS_HIST.get(st.session_state.get("hist_franja", ""), (6, 20))
        r = resumen_historico(None if suc.startswith("Todas") else suc, None if cat.startswith("Todas") else cat,
                              str(d_ini), str(d_fin), h_ini, h_fin)
        df = pd.DataFrame(r["categorias"])
        if not df.empty:
            df.insert(0, "periodo", f"{d_ini} a {d_fin}")
            df.insert(1, "sucursal_filtro", suc)
            df.insert(2, "franja", f"{h_ini:02d}:00-{h_fin:02d}:59")
        return _csv(df)

    if pagina == "Estado de datos y modelo":
        return _csv(pd.DataFrame(cargar_resultados_experimentos()))

    return _csv(pd.DataFrame([
        {"sucursal": d["sucursal"], "fecha": d["fecha"], "categoria": d["categoria"],
         "unidades_estimadas": d["unidades_estimadas"], "unidades_recomendadas": d["unidades_recomendadas"],
         "rango_85_min": d["rango_estimado_85"][0], "rango_85_max": d["rango_estimado_85"][1],
         "ref_historica_dow": d["ref_historica_dow"], "variacion_pct": d["delta_pct_vs_ref"],
         "nivel_demanda": d["nivel_demanda"]}
        for d in resumen["desglose"]
    ]))
