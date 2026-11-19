"""Shell de la aplicación (Aside + Header fijo) replicado del Figma y manejo de estado compartido.

Estado maestro (no-widget) en `st.session_state`:
    nav_page, store_location, product_category, fecha_obj, turno, temp_media, precipitacion,
    usar_rango_termico_manual, temp_min_manual, temp_max_manual

Varios widgets pueden controlar el mismo valor maestro (p. ej. la sucursal aparece en el Aside,
en el Header y en los filtros de algunas vistas). `bound()` crea el widget con su propia key,
le copia el valor maestro antes de instanciarlo y, en `on_change`, escribe de vuelta al maestro.
Así nunca se modifica la key de un widget ya instanciado (lo que lanzaría StreamlitAPIException).
"""

from __future__ import annotations

from datetime import date
from typing import Any, Callable

import pandas as pd
import streamlit as st

from services.backend_bridge import CASOS_DEMO
from ui.theme import html, icon, img_src

SUCURSALES = ["Lower Manhattan", "Hell's Kitchen", "Astoria"]
TURNOS = ["Turno Mañana (06:00 - 14:00)", "Turno Tarde (14:00 - 20:00)"]
PAGINAS: list[tuple[str, str]] = [
    ("Propósito e Incorporación", "explore"),
    ("Resumen operativo", "space_dashboard"),
    ("Pronóstico de demanda", "trending_up"),
    ("Recomendaciones de inventario", "inventory_2"),
    ("Análisis histórico", "history"),
    ("Estado de datos y modelo", "monitoring"),
]
PAGINA_NOMBRES = [p for p, _ in PAGINAS]

DEFAULTS: dict[str, Any] = {
    "nav_page": "Resumen operativo",
    "store_location": "Lower Manhattan",
    "product_category": "Coffee",
    "fecha_obj": date(2023, 6, 26),
    "turno": TURNOS[0],
    "temp_media": 24.0,
    "precipitacion": 15.0,
    "usar_rango_termico_manual": False,
    "temp_min_manual": 20.0,
    "temp_max_manual": 28.0,
    "demo_notice": None,
}


def init_state() -> None:
    for k, v in DEFAULTS.items():
        if k not in st.session_state:
            st.session_state[k] = v


def _copy(widget_key: str, state_key: str) -> None:
    st.session_state[state_key] = st.session_state[widget_key]


def bound(widget_fn: Callable[..., Any], label: str, state_key: str, widget_key: str, **kwargs: Any) -> Any:
    """Crea un widget ligado al valor maestro `state_key` (ver docstring del módulo)."""
    st.session_state[widget_key] = st.session_state[state_key]
    return widget_fn(label, key=widget_key, on_change=_copy, args=(widget_key, state_key), **kwargs)


def ir_a(pagina: str) -> None:
    """Callback de navegación (usable desde botones de cualquier vista)."""
    st.session_state["nav_page"] = pagina


# ----------------------------------------------------------------------------
# Casos demo (RF-05)
# ----------------------------------------------------------------------------
def _cargar_caso_demo(widget_key: str = "w_demo_case") -> None:
    nombre = st.session_state.get(widget_key, "")
    caso = CASOS_DEMO.get(nombre) or CASOS_DEMO["Caso 1: Lunes operativo en Lower Manhattan (Escenario Figma)"]
    st.session_state["store_location"] = caso["store_location"]
    st.session_state["product_category"] = caso["product_category"]
    st.session_state["fecha_obj"] = pd.to_datetime(caso["fecha"]).date()
    st.session_state["temp_media"] = float(caso["temp_media"])
    st.session_state["precipitacion"] = float(caso["precipitacion"])
    st.session_state["turno"] = caso.get("turno", TURNOS[0])
    st.session_state["usar_rango_termico_manual"] = "temp_min" in caso and "temp_max" in caso
    if "temp_min" in caso and "temp_max" in caso:
        st.session_state["temp_min_manual"] = float(caso["temp_min"])
        st.session_state["temp_max_manual"] = float(caso["temp_max"])
    st.session_state["demo_notice"] = f"Caso cargado: {nombre or 'Caso 1'}"


def _calcular() -> None:
    st.session_state["demo_notice"] = (
        f"Inferencia ejecutada: {st.session_state['store_location']} • {st.session_state['product_category']} • "
        f"{st.session_state['fecha_obj']:%Y-%m-%d}"
    )


def render_panel_simulacion(opciones_categoria: list[str], prefijo: str = "", compacto: bool = False) -> None:
    """Formulario de escenario: RF-01 (entradas), RF-02 (disparador), RF-05 (casos demo).

    Se renderiza en el Aside (`prefijo="side_"`, compacto) y en el panel del Header; ambos usan
    keys distintas pero el mismo estado maestro, por lo que siempre muestran los mismos valores.
    """
    k = lambda nombre: f"{prefijo}{nombre}"  # noqa: E731
    if not compacto:
        html(
            f"""<div class="eyebrow brown" style="margin-bottom:2px;">{icon('tune', 16)} Parámetros del escenario (RF-01)</div>
            <p class="small" style="margin:0 0 4px 0;">Los cambios se aplican al instante en todas las vistas.</p>"""
        )
    opciones_demo = [c for c in CASOS_DEMO if CASOS_DEMO[c]]
    st.selectbox("Caso de demostración (RF-05)", opciones_demo, key=k("w_demo_case"))
    st.button("Cargar caso de demostración", icon=":material/bolt:", on_click=_cargar_caso_demo, args=(k("w_demo_case"),),
              width="stretch", key=k("btn_demo"))
    if st.session_state["product_category"] not in opciones_categoria:
        st.session_state["product_category"] = "Coffee"
    cols = [st.container()] * 2 if compacto else st.columns(2)
    with cols[0]:
        bound(st.selectbox, "Sucursal", "store_location", k("w_store_pop"), options=SUCURSALES)
        bound(st.date_input, "Fecha objetivo", "fecha_obj", k("w_fecha"), min_value=date(2023, 1, 1), max_value=date(2023, 12, 31))
    with cols[1]:
        bound(st.selectbox, "Categoría", "product_category", k("w_cat_pop"), options=opciones_categoria)
        bound(st.selectbox, "Jornada operativa", "turno", k("w_turno"), options=TURNOS)
    bound(st.slider, "Temperatura esperada (°C)", "temp_media", k("w_temp"), min_value=-5.0, max_value=40.0, step=0.5)
    bound(st.slider, "Precipitación esperada (mm)", "precipitacion", k("w_rain"), min_value=0.0, max_value=150.0, step=1.0)
    bound(st.checkbox, "Especificar Temp. Mín/Máx manual (RNF-02)", "usar_rango_termico_manual", k("w_manual"))
    if st.session_state["usar_rango_termico_manual"]:
        c1, c2 = st.columns(2)
        with c1:
            bound(st.number_input, "Temp. mínima (°C)", "temp_min_manual", k("w_tmin"), step=0.5)
        with c2:
            bound(st.number_input, "Temp. máxima (°C)", "temp_max_manual", k("w_tmax"), step=0.5)
    st.button("Calcular predicción (RF-02)", icon=":material/play_arrow:", type="primary", on_click=_calcular,
              width="stretch", key=k("btn_calc"))


# ----------------------------------------------------------------------------
# Aside
# ----------------------------------------------------------------------------
def render_sidebar(n_registros: int, opciones_categoria: list[str]) -> None:
    with st.sidebar:
        html(
            f"""
            <div class="side-brand">
                <div class="side-logo">{icon('coffee', 22)}</div>
                <div><div class="side-title">CaféSmart AI</div><div class="side-sub">Demand<br>Intelligence</div></div>
            </div>
            """
        )
        bound(
            st.selectbox,
            "Sucursal activa",
            "store_location",
            "w_store_side",
            options=SUCURSALES,
            format_func=lambda s: f"● Sucursal activa: {s}",
            label_visibility="collapsed",
        )
        iconos = dict(PAGINAS)
        bound(
            st.radio,
            "Navegación",
            "nav_page",
            "nav_radio",
            options=PAGINA_NOMBRES,
            format_func=lambda p: f":material/{iconos[p]}: {p}",
            label_visibility="collapsed",
        )
        with st.expander("Controles de predicción (RF-01)", icon=":material/tune:"):
            render_panel_simulacion(opciones_categoria, prefijo="side_", compacto=True)
        html('<div class="side-spacer" style="min-height:14vh;"></div>')
        avatar = img_src("avatar_gerente.jpg")
        html(
            f"""
            <div class="side-dataset">
                <div class="lbl">DATASET</div>
                <div class="val">Maven (Ene-Jun 2023) • {n_registros / 1000:.0f}k reg.</div>
            </div>
            <div class="side-user">
                <img src="{avatar}" alt="">
                <div><div class="nm">Carlos Méndez</div><div class="rl">GERENTE<br>OPERACIONES</div></div>
                <span class="inf">{icon('info', 20)}</span>
            </div>
            """
        )


# ----------------------------------------------------------------------------
# Header
# ----------------------------------------------------------------------------
def _semana_label(fecha: date) -> str:
    meses = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
    return f"Sem. {fecha.isocalendar().week} • {meses[fecha.month - 1]} {fecha.year}"


def render_header(
    pagina: str,
    opciones_categoria: list[str],
    estado_mx: str,
    export_csv: bytes | None,
    export_name: str,
) -> None:
    """Header fijo: breadcrumb, sucursal, semana (abre parámetros), clima y acción principal."""
    fecha = st.session_state["fecha_obj"]
    temp = float(st.session_state["temp_media"])
    with st.container(key="app_header"):
        cols = st.columns([2.6, 2.3, 2.1, 2.3, 2.1], vertical_alignment="center")
        with cols[0]:
            html('<div class="crumb"><span class="a">PLATAFORMA</span><span class="s">/</span><span class="b">Inteligencia<br>Operativa</span></div>')
        with cols[1]:
            bound(st.selectbox, "Sucursal", "store_location", "w_store_head", options=SUCURSALES, label_visibility="collapsed")
        with cols[2]:
            with st.popover(f":material/calendar_today: {_semana_label(fecha)}", width="stretch", key="hdr_week"):
                render_panel_simulacion(opciones_categoria)
        with cols[3]:
            html(
                f'<div class="hpill clima ok"><span class="b-dot" style="width:7px;height:7px;border-radius:50%;background:#C77C55;display:inline-block;"></span>'
                f'<span class="t">Clima sincronizado<br>({estado_mx} {temp:.0f}°C)</span></div>'
            )
        with cols[4]:
            if pagina == "Propósito e Incorporación":
                st.button(
                    "Ejecutar Simulación",
                    icon=":material/play_arrow:",
                    type="primary",
                    width="stretch",
                    on_click=ir_a,
                    args=("Pronóstico de demanda",),
                    key="hdr_run",
                )
            elif export_csv is not None:
                st.download_button(
                    "Exportar reporte",
                    data=export_csv,
                    file_name=export_name,
                    mime="text/csv",
                    icon=":material/download:",
                    type="primary",
                    width="stretch",
                    key="hdr_export",
                )
