"""Vista 'Pronóstico de demanda' (Figma: Main-8 / Header-8)."""

from __future__ import annotations

import math
from datetime import timedelta
from typing import Any

import pandas as pd
import streamlit as st

from services.backend_bridge import (
    CATEGORY_COLORS,
    generar_curva_horaria,
    generar_tabla_franjas_detalle,
    load_clean_dataset,
    load_transacciones,
    metricas_ganador,
    perfil_horario_real,
    predecir_serie_temporal,
)
from ui.charts import (
    plot_distribucion_categorias_proyectada,
    plot_resumen_demanda_horaria,
    plot_sensibilidad_clima,
    plot_serie_temporal_pronostico,
)
from ui.shell import DEFAULTS, SUCURSALES, bound, ir_a
from ui.theme import badge, html, icon, img_src, page_header

MESES_C = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
DIAS_C = ["LUN", "MAR", "MIÉ", "JUE", "VIE", "SÁB", "DOM"]
FILAS_POR_PAGINA = 5


def _fc(d: Any, anio: bool = False) -> str:
    d = pd.to_datetime(d)
    return f"{d.day:02d} {MESES_C[d.month - 1]}" + (f" {d.year}" if anio else "")


def _reset() -> None:
    for k in ("store_location", "product_category", "fecha_obj", "temp_media", "precipitacion"):
        st.session_state[k] = DEFAULTS[k]
    st.session_state["pron_producto"] = "Todos los productos"
    st.session_state["pron_pagina"] = 1


def _consultar() -> None:
    st.session_state["pron_pagina"] = 1
    st.session_state["demo_notice"] = (
        f"Consulta ejecutada (RF-02): {st.session_state['store_location']} • {st.session_state['product_category']}"
    )


def _pag(delta: int, total: int) -> None:
    st.session_state["pron_pagina"] = min(max(1, st.session_state.get("pron_pagina", 1) + delta), total)


def render(state: dict[str, Any]) -> None:
    store = state["store_location"]
    cat = state["product_category"]
    fecha_str = state["fecha_str"]
    temp, rain = state["temp_media"], state["precipitacion"]
    resumen = state["store_summary"]
    m = metricas_ganador()
    fecha = pd.to_datetime(fecha_str)
    corte = fecha - timedelta(days=1)

    page_header(
        "Pronóstico de demanda",
        "Explora la demanda esperada por sucursal, categoría y franja horaria para apoyar la preparación y optimizar insumos frescos.",
        eyebrow="MODELOS DESCRIPTIVOS &amp; PREDICTIVOS / INFERENCIA V1.0",
        right=f'<div class="surface row mono" style="font-size:14px;color:#1B1C18;padding:14px 20px;">'
        f'<span class="dot" style="background:#7B5641;"></span>Corte de serie: {_fc(corte, True)}, 23:59 EST</div>',
        divider=False,
    )
    html(
        f"""
        <div class="surface between" style="padding:16px 20px;align-items:center;">
          <div class="row p" style="align-items:flex-start;color:#4F4540;">{icon('verified_user', 22, '#7B5641')}
            <span><strong style="color:#1B1C18;">Nota metodológica transparente:</strong> las estimaciones provienen del modelo
            {state['last_prediction']['modelo_usado']} entrenado con partición cronológica estricta (WAPE test = {m['wape']:.2f}%, MAE = {m['mae']:.2f} uds).
            La predicción es un apoyo a la decisión, no una orden de compra obligatoria.</span></div>
          <span class="badge sq b-neutral b-caps">Contrato predecir()</span>
        </div>
        """
    )

    # ---------------- consola de parámetros ----------------
    tx = load_transacciones()
    with st.container(key="card_consola"):
        html(
            f"""<div class="surface between" style="padding:10px 16px;">
            <span class="eyebrow row" style="gap:6px;">{icon('tune', 18, '#4F4540')} Parámetros de consulta multivariada</span>
            <span class="p">Frecuencia calculada: diaria + desagregación horaria</span></div>"""
        )
        c = st.columns([2.1, 2.1, 2.1, 2.0, 2.0, 1.9, 0.7], vertical_alignment="bottom")
        with c[0]:
            bound(st.selectbox, "Sucursal activa", "store_location", "w_store_pron", options=SUCURSALES)
        with c[1]:
            bound(st.selectbox, "Categoría (dataset)", "product_category", "w_cat_pron", options=state["opciones_categoria"])
        with c[2]:
            sub = tx if cat == "Todas las categorías" else tx[tx["product_category"] == cat]
            productos = ["Todos los productos"] + sorted(sub["product_type"].unique().tolist())
            if st.session_state.get("pron_producto") not in productos:
                st.session_state["pron_producto"] = "Todos los productos"
            producto = st.selectbox("Ítem / producto", productos, key="pron_producto")
        with c[3]:
            bound(st.date_input, "Horizonte temporal", "fecha_obj", "w_fecha_pron")
        with c[4]:
            gran = st.segmented_control("Granularidad", ["Diaria", "Horaria"], default="Diaria", key="pron_gran", width="stretch") or "Diaria"
        with c[5]:
            st.button("Consultar", icon=":material/search:", type="primary", on_click=_consultar, width="stretch", key="pron_consultar")
        with c[6]:
            st.button("", icon=":material/restart_alt:", on_click=_reset, key="pron_reset", help="Restablecer escenario base")

    # Factor de desagregación por producto (participación histórica dentro de la categoría y sucursal)
    factor = 1.0
    if producto != "Todos los productos":
        base = sub[sub["store_location"] == store]
        tot = float(base["transaction_qty"].sum()) or 1.0
        factor = float(base[base["product_type"] == producto]["transaction_qty"].sum()) / tot

    serie = predecir_serie_temporal(store, cat, fecha_str, temp, rain, dias_hist=14, dias_futuro=7)
    proj = serie[serie["tipo"] == "Pronóstico"].copy()
    hist = serie[serie["tipo"] == "Histórico real"].copy()
    for col in ("pronostico", "intervalo_min", "intervalo_max", "media_ref"):
        proj[col] = proj[col] * factor
    serie_plot = pd.concat([hist.assign(unidades_reales=hist["unidades_reales"] * factor), proj], ignore_index=True)

    total7 = float(proj["pronostico"].sum())
    dia_pico = proj.loc[proj["pronostico"].idxmax()]
    dia_pico_dt = pd.to_datetime(dia_pico["fecha"])
    perfil = perfil_horario_real(store, cat, int(dia_pico_dt.day_of_week))
    hora_pico = perfil.loc[perfil["share"].idxmax()]
    uds_pico_h = float(dia_pico["pronostico"]) * float(hora_pico["share"])
    fin = fecha + timedelta(days=6)

    # Referencia: mismo día de la semana anterior (observado)
    df_clean = load_clean_dataset()
    ref_dt = fecha - timedelta(days=7)
    mask = (df_clean["store_location"] == store) & (df_clean["fecha"] == ref_dt.strftime("%Y-%m-%d"))
    if cat != "Todas las categorías":
        mask &= df_clean["product_category"] == cat
    ref_obs = float(df_clean.loc[mask, "unidades_vendidas"].sum()) * factor
    pred_dia = float(proj.iloc[0]["pronostico"]) if not proj.empty else 0.0
    ref_badge = ""
    if ref_obs > 0:
        var = (pred_dia - ref_obs) / ref_obs * 100
        ref_badge = badge(f"{icon('trending_up' if var >= 0 else 'trending_down', 14)} {var:+.1f}%", "peach")
        ref_txt = f"Base {_fc(ref_dt)}: {ref_obs:,.0f} uds observadas. Pronóstico del {_fc(fecha)}: {pred_dia:,.0f} uds."
    else:
        ref_txt = "Sin observación real para esa fecha (fuera del histórico Ene-Jun 2023)."
    std = df_clean.loc[(df_clean["store_location"] == store) & (df_clean["fecha"] <= corte.strftime("%Y-%m-%d"))]
    if cat != "Todas las categorías":
        std = std[std["product_category"] == cat]
    std_val = float(std.groupby("fecha")["unidades_vendidas"].sum().tail(28).std() or 0.0) * factor

    html(
        f"""
        <div class="grid-3">
          <div class="kpi"><div>
            <div class="kpi-top"><span class="kpi-label">Total unidades estimadas</span>{icon('bar_chart', 22, '#7B5641')}</div>
            <div class="kpi-value">{total7:,.0f}<span class="kpi-unit">UDS</span></div>
            <div class="row p" style="align-items:flex-start;gap:6px;margin-top:4px;">{icon('location_on', 18, '#4F4540')}<span>{store} • {_fc(fecha)} - {_fc(fin, True)}</span></div></div>
            <div class="between small" style="margin-top:14px;font-size:13.5px;"><span>Pico proyectado: {DIAS[dia_pico_dt.day_of_week]}<br>({hora_pico['hora']})</span>
            <span class="mono" style="color:#7B5641;">~{uds_pico_h:,.0f}<br>uds/h</span></div></div>
          <div class="kpi"><div>
            <div class="kpi-top"><span class="kpi-label">Ref. histórica ({DIAS_C[ref_dt.day_of_week]} ant.)</span>{ref_badge}</div>
            <div class="kpi-value">{ref_obs:,.0f}<span class="kpi-unit">UDS / {DIAS_C[ref_dt.day_of_week]} {ref_dt.day}</span></div>
            <p class="p" style="margin-top:4px;">{ref_txt}</p></div>
            <div class="between small" style="margin-top:14px;font-size:13.5px;"><span>Desvío estándar estimado (28 d)</span><span class="mono" style="color:#1B1C18;">± {std_val:,.0f} uds</span></div></div>
          <div class="kpi"><div>
            <div class="kpi-top"><span class="kpi-label">Incertidumbre del pronóstico</span>{icon('help', 22, '#81756F')}</div>
            <div class="row" style="margin-top:14px;gap:10px;"><span class="dot" style="background:#72856B;width:12px;height:12px;"></span><span class="h3" style="font-size:20px;">Modelo validado</span></div>
            <p class="p" style="margin-top:6px;">Bandas al 85% de confianza empírica. Confiabilidad en test: <strong>MAPE {m['mape_core']:.2f}%</strong> (categorías principales) • WAPE {m['wape']:.2f}%.</p></div>
            <div class="between small" style="margin-top:14px;font-size:13.5px;"><span>Horizonte de predicción</span><span class="mono" style="color:#1B1C18;">t + 7 días</span></div></div>
        </div>
        """
    )

    # ---------------- fotos + hallazgo ----------------
    desg = {d["categoria"]: d for d in resumen["desglose"]}
    coffee_7d = float(predecir_serie_temporal(store, "Coffee", fecha_str, temp, rain, dias_hist=1, dias_futuro=7)
                      .query("tipo == 'Pronóstico'")["pronostico"].sum())
    bakery_dia = float(desg.get("Bakery", {}).get("unidades_estimadas", 0.0))
    perfil_bak = perfil_horario_real(store, "Bakery", int(fecha.day_of_week))
    horneo = bakery_dia * float(perfil_bak[perfil_bak["hora_int"] <= 11]["share"].sum())
    perfil_dia = perfil_horario_real(store, cat, int(fecha.day_of_week))
    franja = perfil_dia[(perfil_dia["hora_int"] >= 8) & (perfil_dia["hora_int"] < 10)]["share"].sum() * 100
    refuerzo_h = max(6, int(hora_pico["hora_int"]) - 1)
    html(
        f"""
        <div style="display:grid;grid-template-columns:1fr 1fr 1.45fr;gap:14px;">
          <div class="photo" style="background-image:url('{img_src('insumo_grano.jpg')}');min-height:240px;">
            <div class="cap"><div class="e">INSUMO CLAVE</div><div class="t">Grano tueste medio: {coffee_7d * 0.0185:,.0f} kg necesarios (7 días)</div></div></div>
          <div class="photo" style="background-image:url('{img_src('bolleria_matutina.jpg')}');min-height:240px;">
            <div class="cap"><div class="e">BOLLERÍA MATUTINA</div><div class="t">Horneo inicial: {horneo:,.0f} unidades recomendadas</div></div></div>
          <div class="surface" style="padding:22px 24px;border-radius:8px;">
            <div class="between" style="align-items:flex-start;">
              <div class="row" style="align-items:flex-start;">{icon('lightbulb', 24, '#4F4540')}<span class="h3" style="font-size:20px;">Hallazgo para el turno de apertura</span></div>
              {badge('Alerta de dotación', 'peach')}</div>
            <p class="p" style="font-size:15px;line-height:23px;margin-top:10px;">La franja 08:00 - 10:00 concentra el {franja:.0f}% del volumen diario de
              <strong>{cat}</strong> en {store} (perfil observado de los {DIAS[fecha.day_of_week].lower()}s). El pico del horizonte se espera el
              {DIAS[dia_pico_dt.day_of_week].lower()} {_fc(dia_pico_dt)} a las {hora_pico['hora']}.</p>
            <div class="row p" style="gap:18px;margin-top:12px;color:#1B1C18;flex-wrap:wrap;">
              <span class="row" style="gap:6px;">{icon('check_circle', 18)} Plan de molienda calibrado</span>
              <span class="row" style="gap:6px;">{icon('schedule', 18)} Refuerzo barista sugerido: {refuerzo_h:02d}:30</span></div>
          </div>
        </div>
        """
    )

    # ---------------- gráfica ----------------
    with st.container(key="card_chart_pron"):
        h1, h2 = st.columns([6.5, 3.5], vertical_alignment="top")
        with h1:
            html(
                f"""<div class="row" style="align-items:flex-start;gap:14px;"><h3 class="h2">Ventas históricas observadas vs Pronóstico de demanda</h3>
                <span class="badge sq b-neutral b-caps" style="white-space:normal;">{store}</span></div>
                <p class="p" style="margin-top:6px;">Evolución de 21 días: 14 días de ventas reales de Maven ({_fc(hist['fecha'].iloc[0]) if not hist.empty else '-'} - {_fc(corte)})
                seguidos de la proyección del modelo ({_fc(fecha)} - {_fc(fin)}).{' Producto: <strong>' + producto + '</strong> (desagregado por participación histórica).' if factor != 1.0 else ''}</p>"""
            )
        with h2:
            vista = st.segmented_control(
                "Gráfica",
                ["Serie", "Por categoría", "Clima"],
                default="Serie",
                key="pron_graf",
                label_visibility="collapsed",
                width="stretch",
            ) or "Serie"
        if gran == "Horaria" and vista == "Serie":
            p = state["last_prediction"]
            fig = plot_resumen_demanda_horaria(
                generar_curva_horaria(p["unidades_estimadas"] * factor, p["ref_historica_dow"] * factor, store,
                                      cat, fecha_str, [x * factor for x in p["rango_estimado_85"]])
            )
        elif vista == "Serie":
            fig = plot_serie_temporal_pronostico(serie_plot)
        elif vista == "Por categoría":
            fig = plot_distribucion_categorias_proyectada(resumen["desglose"])
        else:
            cat_cl = "Coffee" if cat == "Todas las categorías" else cat
            fig = plot_sensibilidad_clima(df_clean, store, cat_cl, temp, rain, state["last_prediction"]["unidades_estimadas"])
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
        html(
            f"""<div class="surface between" style="padding:12px 16px;">
            <span class="row p" style="gap:8px;">{icon('info', 18)} * Los días con asterisco son demanda pronosticada por el modelo; la banda sombreada es el intervalo empírico al 85%.</span>
            <span class="mono small" style="color:#4F4540;">Intervalo de confianza: 85%</span></div>"""
        )

    # ---------------- tabla por franja ----------------
    df_fr = generar_tabla_franjas_detalle(store, fecha_str, resumen["desglose"])
    if cat != "Todas las categorías":
        df_fr = df_fr[df_fr["categoria"] == cat] if (df_fr["categoria"] == cat).any() else df_fr
    with st.container(key="card_tabla_pron"):
        t1, t2, t3 = st.columns([5.4, 2.3, 2.3], vertical_alignment="center")
        with t1:
            html(
                f"""<div class="row" style="gap:12px;"><h3 class="h2">Detalle del pronóstico por franja horaria</h3>
                <span class="badge sq b-sage">{DIAS[fecha.day_of_week]} {fecha.day} {MESES_C[fecha.month - 1]} {fecha.year}</span></div>
                <p class="p" style="margin-top:4px;">Desglose granular para el armado de mise-en-place y cronograma de tostado matutino.</p>"""
            )
        with t2:
            with st.popover("Filtrar alertas", icon=":material/filter_list:", width="stretch"):
                filtro = st.radio("Mostrar", ["Todas", "Solo demanda alta / atípica", "Demanda habitual"], key="pron_filtro")
        if filtro == "Solo demanda alta / atípica":
            df_fr = df_fr[df_fr["nivel"] != "Habitual"]
        elif filtro == "Demanda habitual":
            df_fr = df_fr[df_fr["nivel"] == "Habitual"]
        nombre_base = store.replace(" ", "_").replace("'", "")
        with t3:
            st.download_button("Exportar (.CSV)", df_fr.to_csv(index=False).encode("utf-8-sig"),
                               file_name=f"pronostico_franjas_{nombre_base}_{fecha_str}.csv",
                               icon=":material/download:", width="stretch", key="pron_csv")
        total_pag = max(1, math.ceil(len(df_fr) / FILAS_POR_PAGINA))
        pag = min(st.session_state.get("pron_pagina", 1), total_pag)
        vista_df = df_fr.iloc[(pag - 1) * FILAS_POR_PAGINA: pag * FILAS_POR_PAGINA]
        filas = []
        for _, r in vista_df.iterrows():
            if r["nivel"] == "Alta":
                est = f'<span class="badge sq b-amber" style="white-space:normal;">! {r["estado_explicativo"]}</span>'
                uds_color = "#A3661C"
            elif r["nivel"] == "Baja":
                est = f'<span class="badge sq b-neutral" style="white-space:normal;"><span class="b-dot"></span>{r["estado_explicativo"]}</span>'
                uds_color = "#1B1C18"
            else:
                est = f'<span class="badge sq b-sage" style="white-space:normal;"><span class="b-dot"></span>{r["estado_explicativo"]}</span>'
                uds_color = "#1B1C18"
            filas.append(
                f"""<tr><td class="mono" style="white-space:nowrap;font-size:13.5px;">{icon('schedule', 18, '#4F4540')} {r['fecha_franja']}</td><td style="font-size:13.5px;">{r['sucursal']}</td>
                <td><span class="row" style="gap:8px;"><span class="dot" style="background:{CATEGORY_COLORS.get(r['categoria'], '#81756F')};"></span>{r['categoria']}</span></td>
                <td class="num" style="color:{uds_color};font-weight:600;">{r['unidades_estimadas']} uds</td>
                <td class="num" style="color:#81756F;">{r['ref_historica']} uds</td><td style="max-width:240px;">{est}</td></tr>"""
            )
        html(
            f"""<div class="tbl-wrap" style="box-shadow:none;border-left:none;border-right:none;border-radius:0;margin:6px -22px 0 -22px;">
            <table class="tbl"><thead><tr><th>Fecha / franja</th><th>Sucursal</th><th>Categoría</th><th class="r">Unidades<br>estimadas</th>
            <th class="r">Ref.<br>histórica</th><th>Estado explicativo</th></tr></thead><tbody>{''.join(filas) or '<tr><td colspan="6" class="p">Sin franjas para el filtro seleccionado.</td></tr>'}</tbody></table></div>"""
        )
        f1, f2, f3, f4, f5 = st.columns([4.6, 0.5, 1.3, 0.5, 3.1], vertical_alignment="center")
        with f1:
            html(f'<span class="mono p"><strong style="color:#1B1C18;">{len(vista_df)}</strong> de {len(df_fr)} franjas horarias cargadas</span>')
        with f2:
            st.button("", icon=":material/chevron_left:", on_click=_pag, args=(-1, total_pag), disabled=pag <= 1, key="pron_prev")
        with f3:
            html(f'<div style="text-align:center;font-weight:600;color:#1B1C18;">Página {pag} de {total_pag}</div>')
        with f4:
            st.button("", icon=":material/chevron_right:", on_click=_pag, args=(1, total_pag), disabled=pag >= total_pag, key="pron_next")
        with f5:
            st.download_button("Descargar consulta (.CSV)", df_fr.to_csv(index=False).encode("utf-8-sig"),
                               file_name=f"consulta_{nombre_base}_{fecha_str}.csv",
                               icon=":material/download:", type="tertiary", key="pron_csv2")

    # ---------------- CTA ----------------
    with st.container(key="surface_cta_pron"):
        a, b, cc = st.columns([6, 1.4, 3.2], vertical_alignment="center")
        with a:
            html(
                f"""<div class="row" style="align-items:flex-start;gap:14px;">
                <span style="background:#FCEEE6;border-radius:8px;padding:8px;">{icon('sync_alt', 22, '#C77C55')}</span>
                <div><div class="eyebrow">Integración en cadena de suministro</div>
                <div class="p" style="font-size:16px;color:#1B1C18;">¿Deseas conectar este pronóstico directamente con el plan de compras de ingredientes perecederos?</div></div></div>"""
            )
        with b:
            html(badge("Conexión lista", "sage", dot=True))
        with cc:
            st.button("Ir a Recomendaciones de Inventario", icon=":material/arrow_forward:", icon_position="right",
                      on_click=ir_a, args=("Recomendaciones de inventario",), width="stretch", key="pron_go_recs")
