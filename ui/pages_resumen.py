"""Vista 'Resumen operativo' (Figma: Main-10 / Header-10)."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from services.backend_bridge import (
    STORE_METADATA,
    describir_curva_horaria,
    generar_curva_horaria,
    items_revision_stock,
    load_transacciones,
    metricas_ganador,
    predecir_serie_temporal,
)
from ui.charts import plot_resumen_demanda_horaria, plot_serie_temporal_pronostico
from ui.shell import ir_a
from ui.theme import badge, html, icon, page_header

DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
DIAS_PL = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábados", "domingos"]
MESES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
MESES_C = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]


def fecha_larga(fecha_str: str) -> str:
    dt = pd.to_datetime(fecha_str)
    return f"{DIAS[dt.day_of_week]} {dt.day:02d} de {MESES[dt.month - 1]} de {dt.year}"


def _legend(items: list[tuple[str, str]]) -> str:
    out = []
    for kind, label in items:
        if kind == "line":
            sw = '<span style="width:18px;height:2px;background:#22140D;display:inline-block;"></span>'
        elif kind == "dash":
            sw = '<span style="width:18px;border-top:2px dashed #C77C55;display:inline-block;"></span>'
        else:
            sw = '<span style="width:14px;height:14px;background:#FAEDE6;border:1px solid #EDD4C7;display:inline-block;"></span>'
        color = "#C77C55" if kind == "dash" else "#1B1C18"
        out.append(f'<span class="row" style="gap:8px;font-size:14px;color:{color};">{sw}{label}</span>')
    return '<div style="display:flex;flex-wrap:wrap;gap:8px 22px;max-width:440px;">' + "".join(out) + "</div>"


def render(state: dict[str, Any]) -> None:
    store = state["store_location"]
    fecha_str = state["fecha_str"]
    temp = state["temp_media"]
    rain = state["precipitacion"]
    turno = state["turno"]
    resumen = state["store_summary"]
    pred = state["last_prediction"]
    meta = STORE_METADATA.get(store, STORE_METADATA["Lower Manhattan"])
    m = metricas_ganador()
    dt = pd.to_datetime(fecha_str)
    dia_pl = DIAS_PL[dt.day_of_week]

    page_header(
        "Resumen operativo",
        "Consulta la demanda, revisa las condiciones del día y planifica la preparación por turno.",
        title_badge=badge(f"Motor IA activo • {pred['modelo_usado']} • MAPE {m['mape_core']:.2f}% • WAPE {m['wape']:.2f}%", "peach"),
        right=f'<div class="row small" style="font-weight:600;letter-spacing:.06em;color:#4F4540;font-size:13px;">'
        f'<span class="dot" style="background:#6E625B;"></span>Última inferencia: {dt.day:02d} {MESES_C[dt.month-1]} {dt.year} • '
        f'{resumen["tiempo_total_ms"]:.0f} ms</div>',
    )

    # ---- barra de contexto (sucursal / jornada / modo) ----
    with st.container(key="surface_ctx"):
        c1, c2, c3 = st.columns([3, 4.4, 3.4], vertical_alignment="center")
        with c1:
            html(
                f'<div class="hpill" style="background:#fff;border:1px solid #E9E7E0;">{icon("location_on", 18, "#81756F")}'
                f'<span class="eyebrow">Sucursal:</span><span class="t">{store} (Seleccionada)</span></div>'
            )
        with c2:
            html(
                f'<div class="hpill" style="background:#fff;border:1px solid #E9E7E0;">{icon("calendar_month", 18, "#81756F")}'
                f'<span class="eyebrow">Jornada:</span><span class="t" style="white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">'
                f'{fecha_larga(fecha_str)} — {turno.split(" (")[0]} ({turno.split("(")[-1]}</span></div>'
            )
        with c3:
            modo = st.segmented_control(
                "Modo de vista",
                ["Por franja horaria", "Vista diaria"],
                default="Por franja horaria",
                label_visibility="collapsed",
                key="resumen_modo",
                width="stretch",
            ) or "Por franja horaria"

    # ---- KPIs ----
    total_ref = resumen["total_ref_historica"]
    total_est = resumen["total_unidades_estimadas"]
    delta = resumen["delta_total_pct"]
    alertas = items_revision_stock(resumen["desglose"])
    nivel = resumen["nivel_demanda_global"]
    # RF-03: semáforo de tráfico previsto (verde = baja, ámbar = habitual, rojo = alta)
    semaforo = {"Demanda Baja": ("#4E6847", "#E2EBDC", "Baja"), "Demanda Habitual": ("#A3661C", "#FBF0E2", "Habitual"),
                "Demanda Alta": ("#BA1A1A", "#FBE9E6", "Alta")}.get(nivel, ("#A3661C", "#FBF0E2", "Habitual"))
    nivel_html = (f'<span class="badge" style="background:{semaforo[1]};color:{semaforo[0]};">'
                  f'<span class="b-dot"></span>{semaforo[2]}</span>')
    lluvia_txt = "Lluvia intensa" if rain >= 35 else ("Lluvia moderada" if rain >= 10 else ("Lluvia ligera" if rain > 0 else "Sin lluvia"))
    stock_color = "#BA1A1A" if alertas else "#72856B"
    stock_detalle = ", ".join(a["categoria"] for a in alertas[:3]) if alertas else "Sin categorías en Demanda Alta."
    html(
        f"""
        <div class="grid-5">
          <div class="kpi"><div>
              <div class="kpi-top"><span class="kpi-label">Ref. histórico</span>{icon('history', 20, '#81756F')}</div>
              <div class="kpi-value">{total_ref:,.0f}<span class="kpi-unit">uds</span></div></div>
            <div class="kpi-foot">Promedio {dia_pl} habituales en {store}.</div></div>
          <div class="kpi"><div>
              <div class="kpi-top"><span class="kpi-label" style="color:#C77C55;">Demanda<br>estimada</span>{nivel_html}</div>
              <div class="kpi-value">{total_est:,.0f}<span class="kpi-unit">uds</span></div></div>
            <div class="kpi-foot row" style="gap:8px;"><span class="mono" style="color:#7B5641;">{delta:+.1f}%</span><span>vs. referencia media</span></div></div>
          <div class="kpi"><div>
              <div class="kpi-top"><span class="kpi-label">Mayor volumen<br>previsto</span>{icon('local_cafe', 20, '#4F4540')}</div>
              <div class="kpi-value" style="font-size:34px;">{resumen['categoria_lider']}</div></div>
            <div class="kpi-foot"><strong>{resumen['categoria_lider_unidades']:,.0f} uds</strong> estimadas (~{resumen['categoria_lider_share']:.0f}% del volumen del día).</div></div>
          <div class="kpi"><div>
              <div class="kpi-top"><span class="kpi-label" style="color:{stock_color};">Revisión de stock</span>
                <span style="width:20px;height:20px;border-radius:50%;background:{'#FBE9E6' if alertas else '#E2EBDC'};color:{stock_color};display:flex;align-items:center;justify-content:center;font-weight:700;font-size:13px;">{'!' if alertas else '✓'}</span></div>
              <div class="kpi-value" style="color:{stock_color};">{len(alertas)}<span class="kpi-unit">ítems</span></div></div>
            <div class="kpi-foot" style="white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{stock_detalle}</div></div>
          <div class="kpi"><div>
              <div class="kpi-top"><span class="kpi-label">Meteorología</span>{icon('partly_cloudy_day', 20, '#81756F')}</div>
              <div class="kpi-value sm">{temp:.0f}°C • {rain:.0f}mm</div></div>
            <div class="kpi-foot" style="color:#81756F;">{lluvia_txt} • {meta['estado_mx']} (escenario simulado).</div></div>
        </div>
        """
    )

    # ---- gráfica principal ----
    cat_focus = state["product_category"]
    if cat_focus == "Todas las categorías":
        uds_pred, uds_ref, rango = total_est, total_ref, resumen["rango_total_85"]
    else:
        uds_pred, uds_ref, rango = pred["unidades_estimadas"], pred["ref_historica_dow"], pred["rango_estimado_85"]
    df_h = generar_curva_horaria(uds_pred, uds_ref, store, cat_focus, fecha_str, rango)
    info = describir_curva_horaria(df_h)
    n_dias = int(load_transacciones()["fecha_dt"].nunique())

    with st.container(key="card_chart_resumen"):
        horario = "HORARIO 06:00 A 20:00 HRS" if modo == "Por franja horaria" else "SERIE DIARIA 14D + 7D"
        html(
            f"""
            <div class="between" style="align-items:flex-start;flex-wrap:wrap;gap:16px;border-bottom:1px solid #E9E7E0;padding-bottom:16px;">
              <div style="max-width:720px;">
                <div class="row" style="gap:14px;align-items:baseline;flex-wrap:wrap;">
                  <h3 class="h3" style="font-size:20px;">Comparativa: Demanda histórica observada vs. Pronóstico estimado</h3>
                  <span class="eyebrow">• {horario}</span></div>
                <p class="p" style="margin-top:6px;">{dia_pl.capitalize()} típico consolidado vs. proyección {'horaria' if modo == 'Por franja horaria' else 'diaria'} calculada por el modelo para {store} • categoría en foco: <strong>{cat_focus}</strong>.</p>
              </div>
              {_legend([('line', 'Histórico observado'), ('dash', 'Pronóstico proyectado'), ('box', 'Rango de incertidumbre (85%)')])}
            </div>
            """
        )
        if modo == "Por franja horaria":
            fig = plot_resumen_demanda_horaria(df_h)
        else:
            fig = plot_serie_temporal_pronostico(
                predecir_serie_temporal(store, cat_focus, fecha_str, temp, rain)
            )
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
        html(
            f"""
            <div style="border-top:1px solid #E9E7E0;padding-top:12px;">
              <div class="row p" style="gap:8px;">{icon('info', 18, '#81756F')}Pico estimado a las {info['hora_pico']} (~{info['uds_pico']} uds/h; {delta:+.1f}% vs {dia_pl} regular). Valle previsto a las {info['hora_valle']} (~{info['uds_valle']} uds/h).</div>
              <div class="eyebrow" style="margin-top:8px;text-transform:none;letter-spacing:.04em;">Muestra: {n_dias} días de transacciones Maven (Ene-Jun 2023)</div>
            </div>
            """
        )

    # ---- tarjetas inferiores ----
    left, right = st.columns([5, 7.4], gap="medium")
    t_min, t_max = pred["temp_min"], pred["temp_max"]
    prob_lbl = lluvia_txt + " (escenario)"
    cielo = "Lluvioso" if rain >= 35 else ("Parcialmente nublado" if rain >= 10 else "Despejado")
    cielo_icon = "rainy" if rain >= 35 else ("partly_cloudy_day" if rain >= 10 else "sunny")
    with left:
        html(
            f"""
            <div class="card" style="height:100%;">
              <div class="between" style="border-bottom:1px solid #E9E7E0;padding-bottom:12px;align-items:flex-start;">
                <div class="row" style="align-items:flex-start;">{icon('device_thermostat', 22, '#4F4540')}<h3 class="h3" style="font-size:20px;">Contexto climático<br>({meta['estado_mx']})</h3></div>
                {badge('Simulación activa', 'neutral').replace('badge', 'badge sq')}
              </div>
              <p class="p" style="margin:14px 0;">Variables de temperatura y lluvia del escenario activo, acopladas como covariables al modelo de regresión.</p>
              <div class="grid-3" style="gap:10px;">
                <div class="surface" style="text-align:center;"><div class="eyebrow">Temp.<br>esperada</div>
                  <div class="mono" style="font-size:28px;color:#22140D;margin:6px 0;">~{temp:.0f}°C</div>
                  <div class="small">Máx {t_max:.0f}° / Mín {t_min:.0f}°</div></div>
                <div class="surface" style="text-align:center;"><div class="eyebrow">Precipitación</div>
                  <div class="mono" style="font-size:28px;color:#22140D;margin:6px 0;">{rain:.0f}mm</div>
                  <div class="small">{prob_lbl}</div></div>
                <div class="surface" style="text-align:center;"><div class="eyebrow">Cielo</div>
                  <div style="margin:8px 0;">{icon(cielo_icon, 28, '#4F4540')}</div>
                  <div class="small">{cielo}</div></div>
              </div>
              <div class="surface" style="margin-top:14px;font-size:14px;color:#4F4540;line-height:20px;">
                {icon('dataset', 18, '#4F4540')} <strong style="color:#1B1C18;">Aviso de prototipo:</strong> el clima proviene del dataset estatal mensual
                ({store} → {meta['estado_mx']}). Ajusta el escenario desde <em>Semana (Demostración)</em> en el header.
              </div>
            </div>
            """
        )
    top2 = [d["categoria"] for d in resumen["desglose"][:2]]
    coffee = next((d["unidades_estimadas"] for d in resumen["desglose"] if d["categoria"] == "Coffee"), 0.0)
    bakery = next((d["unidades_estimadas"] for d in resumen["desglose"] if d["categoria"] == "Bakery"), 0.0)
    with right:
        with st.container(key="card_reco_resumen"):
            html(
                f"""
                <div class="between" style="border-bottom:1px solid #E9E7E0;padding-bottom:12px;align-items:flex-start;">
                  <div class="row" style="align-items:flex-start;">{icon('assignment_turned_in', 22, '#72856B')}<h3 class="h3" style="font-size:20px;">Recomendación destacada —<br>Planificación del día</h3></div>
                  <span class="badge sq b-sage">Orientativa • IA activa</span>
                </div>
                <div class="surface" style="padding:18px 20px;margin-top:4px;">
                  <div class="row" style="align-items:flex-start;">{icon('soup_kitchen', 24, '#C77C55')}
                    <div><div class="h3" style="font-size:19px;">Refuerzo temprano en barra y repostería</div>
                    <p class="p" style="font-size:15px;line-height:23px;margin-top:4px;">Revisa la preparación de las categorías con mayor demanda estimada (<strong style="color:#1B1C18;">{' y '.join(top2)}</strong>)
                    antes del pico de las <span class="mono" style="color:#1B1C18;">{info['hora_pico']} hrs</span> y del cambio de turno de las
                    <span class="mono" style="color:#1B1C18;">14:00 hrs</span>. Mantén atención en el stock de granos tueste medio para evitar cuellos de botella en la molienda principal.</p></div>
                  </div>
                </div>
                <div class="grid-2" style="margin-top:6px;">
                  <div class="row p" style="align-items:flex-start;color:#1B1C18;">{icon('check_circle', 22, '#72856B')}<span>Molienda batch inicial: {coffee * 0.0185:.1f} kg calibrados</span></div>
                  <div class="row p" style="align-items:flex-start;color:#1B1C18;">{icon('warning', 22, '#BA1A1A')}<span>Croissant mantequilla: lote mínimo de {max(12, int(round(bakery * 0.24)))} uds</span></div>
                </div>
                <div class="hr" style="margin-top:18px;"></div>
                """
            )
            b1, b2 = st.columns(2)
            with b1:
                st.button("Ir a recomendaciones detalladas", icon=":material/arrow_forward:", icon_position="right", type="primary",
                          on_click=ir_a, args=("Recomendaciones de inventario",), key="res_go_recs")
            with b2:
                st.button("Ver desglose por categoría", icon=":material/pie_chart:", type="tertiary",
                          on_click=ir_a, args=("Pronóstico de demanda",), key="res_go_pron")
