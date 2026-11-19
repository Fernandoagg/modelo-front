"""Aplicación Frontend Principal de CaféSmart AI (Streamlit + Plotly).

Réplica de los mockups de alta fidelidad de Figma (IA-CafeSmart): Aside + Header fijo + 6 vistas.
Se conecta de forma desacoplada (RNF-03) con el motor predictivo en `../modelo` vía `services.backend_bridge`.
"""

from __future__ import annotations

from datetime import date
from typing import Any

import streamlit as st

from services.backend_bridge import (
    CORE_CATEGORIES,
    STORE_METADATA,
    ejecutar_inferencia,
    load_feature_defaults,
    load_transacciones,
    predecir_desglose_tienda,
)
from ui import pages
from ui.shell import PAGINA_NOMBRES, init_state, render_header, render_sidebar
from ui.theme import inject_theme

st.set_page_config(
    page_title="CaféSmart AI — Demand Intelligence",
    page_icon="☕",
    layout="wide",
    initial_sidebar_state="expanded",
)


def _validar_entradas() -> tuple[float | None, float | None, list[tuple[str, str]]]:
    """RNF-02: valida el escenario y devuelve (temp_min, temp_max, avisos) sin interrumpir la sesión."""
    avisos: list[tuple[str, str]] = []
    fecha = st.session_state["fecha_obj"]
    if fecha < date(2023, 1, 15):
        avisos.append(("warning", "Aviso de ventana de calentamiento (RNF-02): entre el 01 y el 14 de enero de 2023 los rezagos (Lag-14) "
                                   "aún no existen; el motor usa valores de referencia histórica."))
    elif fecha > date(2023, 7, 31):
        avisos.append(("warning", "Aviso de horizonte extendido (RNF-02): la fecha supera 30 días posteriores al corte (30 Jun 2023); "
                                   "se usan los rezagos estabilizados del cierre de junio."))
    t_min = t_max = None
    if st.session_state["usar_rango_termico_manual"]:
        tmin, tmax = float(st.session_state["temp_min_manual"]), float(st.session_state["temp_max_manual"])
        if tmax < tmin:
            avisos.append(("error", f"Error de validación meteorológica (RNF-02): la temperatura máxima ({tmax} °C) no puede ser menor "
                                    f"que la mínima ({tmin} °C). Se aplica el rango térmico de referencia oficial."))
        else:
            t_min, t_max = tmin, tmax
    return t_min, t_max, avisos


def main() -> None:
    init_state()
    inject_theme()

    defaults = load_feature_defaults()
    categorias = CORE_CATEGORIES + [c for c in defaults["categorias_validas"] if c not in CORE_CATEGORIES]
    opciones_categoria = ["Todas las categorías"] + categorias
    if st.session_state["nav_page"] not in PAGINA_NOMBRES:
        st.session_state["nav_page"] = "Resumen operativo"

    render_sidebar(len(load_transacciones()))

    store = st.session_state["store_location"]
    fecha_str = st.session_state["fecha_obj"].strftime("%Y-%m-%d")
    temp = float(st.session_state["temp_media"])
    rain = float(st.session_state["precipitacion"])
    categoria = st.session_state["product_category"]
    t_min, t_max, avisos = _validar_entradas()

    try:
        payload: dict[str, Any] = {
            "store_location": store,
            "product_category": "Coffee" if categoria == "Todas las categorías" else categoria,
            "fecha": fecha_str,
            "temp_media": temp,
            "precipitacion": rain,
        }
        if t_min is not None and t_max is not None:
            payload.update(temp_min=t_min, temp_max=t_max)
        last_prediction = ejecutar_inferencia(payload)
        store_summary = predecir_desglose_tienda(store, fecha_str, temp, rain, temp_min=t_min, temp_max=t_max)
    except Exception as exc:  # noqa: BLE001 - RNF-02: nunca romper la sesión
        render_header(st.session_state["nav_page"], opciones_categoria, STORE_METADATA[store]["estado_mx"], None, "")
        st.error(f"Entrada fuera de rango (RNF-02): {exc}")
        return

    state: dict[str, Any] = {
        "store_location": store,
        "product_category": categoria,
        "fecha_str": fecha_str,
        "temp_media": temp,
        "precipitacion": rain,
        "turno": st.session_state["turno"],
        "last_prediction": last_prediction,
        "store_summary": store_summary,
        "opciones_categoria": opciones_categoria,
    }

    pagina = st.session_state["nav_page"]
    export = pages.export_csv(pagina, state)
    nombre_csv = f"cafesmart_{pagina.split()[0].lower()}_{store.replace(' ', '_').replace(chr(39), '')}_{fecha_str}.csv"
    render_header(pagina, opciones_categoria, STORE_METADATA[store]["estado_mx"], export, nombre_csv)

    if st.session_state.get("demo_notice"):
        st.toast(st.session_state["demo_notice"], icon="☕")
        st.session_state["demo_notice"] = None
    for kind, msg in avisos:
        (st.error if kind == "error" else st.warning)(msg)

    pages.render(pagina, state)


if __name__ == "__main__":
    main()
