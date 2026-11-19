"""Vista 'Análisis histórico' (Figma: Main-6 / Header-6). Todo se calcula del CSV real de Maven."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from services.backend_bridge import (
    CATEGORY_COLORS,
    STORE_STATE_MAP,
    cargar_resumen_experimentos,
    load_transacciones,
    resumen_historico,
)
from ui.charts import plot_historico_curva_intradia, plot_historico_evolucion_semestral
from ui.theme import html, icon, page_header

MESES_C = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
DIAS_C = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
FRANJAS = {
    "Todo el día (06:00 - 20:00)": (6, 20),
    "Turno Mañana (06:00 - 14:00)": (6, 13),
    "Turno Tarde (14:00 - 20:00)": (14, 20),
}
ICONO_TIENDA = {"Lower Manhattan": "corporate_fare", "Hell's Kitchen": "theater_comedy", "Astoria": "account_balance"}
COLOR_TIENDA = ["#382820", "#7B5641", "#81756F"]


def _fc(d: Any) -> str:
    d = pd.to_datetime(d)
    return f"{d.day:02d} {MESES_C[d.month - 1]}"


def _reset_filtros(min_d: Any, max_d: Any) -> None:
    st.session_state["hist_rango"] = (min_d, max_d)
    st.session_state["hist_store"] = "Todas las sucursales (3)"
    st.session_state["hist_cat"] = "Todas las categorías"
    st.session_state["hist_franja"] = list(FRANJAS)[0]


def _perfil_estacional(hora_pico: str, cat: str) -> str:
    h = int(hora_pico[:2]) if hora_pico[:2].isdigit() else 0
    if cat in ("Coffee", "Bakery") or h <= 10:
        return f"Pico {h:02d}h matutino"
    if 11 <= h <= 15:
        return f"Pico {h:02d}h mediodía"
    return f"Pico {h:02d}h vespertino"


def render(state: dict[str, Any]) -> None:
    tx = load_transacciones()
    min_d, max_d = tx["fecha_dt"].min().date(), tx["fecha_dt"].max().date()
    meta = cargar_resumen_experimentos()

    page_header(
        "Análisis histórico",
        "Explora las tendencias, estacionalidad semanal y distribución de ventas en las tres sucursales durante el primer semestre operativo.",
        eyebrow=f'<span class="num-chip">04</span> Inteligencia de datos retrospectiva',
        right=f"""<div class="card tight row" style="gap:12px;align-items:flex-start;">{icon('database', 22, '#7B5641')}
              <div><div class="small" style="font-size:11px;letter-spacing:.06em;">FUENTE CERTIFICADA</div>
              <div class="mono" style="font-size:14px;color:#1B1C18;line-height:20px;">Coffee Shop Sales (Maven) • {len(tx):,d}<br>transacciones • Ene - Jun 2023</div></div></div>""",
    )

    # ---------------- filtros (form: aplicar / restablecer) ----------------
    st.session_state.setdefault("hist_rango", (min_d, max_d))
    with st.container(key="card_filtros_hist"):
        with st.form("form_hist", border=False):
            c = st.columns([2.3, 2.0, 2.0, 2.2, 1.8, 2.0], vertical_alignment="bottom")
            with c[0]:
                st.date_input("Rango de fechas", min_value=min_d, max_value=max_d, key="hist_rango")
            with c[1]:
                st.selectbox("Sucursal", ["Todas las sucursales (3)", "Lower Manhattan", "Hell's Kitchen", "Astoria"], key="hist_store")
            with c[2]:
                st.selectbox("Categoría de producto", ["Todas las categorías"] + sorted(tx["product_category"].unique()), key="hist_cat")
            with c[3]:
                st.selectbox("Franja horaria", list(FRANJAS), key="hist_franja")
            with c[4]:
                st.form_submit_button("Restablecer", icon=":material/restart_alt:", width="stretch",
                                      on_click=_reset_filtros, args=(min_d, max_d))
            with c[5]:
                st.form_submit_button("Aplicar filtros", icon=":material/tune:", type="primary", width="stretch")

    rango = st.session_state["hist_rango"]
    d_ini, d_fin = (rango if isinstance(rango, (tuple, list)) and len(rango) == 2 else (min_d, max_d))
    store_f = None if st.session_state["hist_store"].startswith("Todas") else st.session_state["hist_store"]
    cat_f = None if st.session_state["hist_cat"] == "Todas las categorías" else st.session_state["hist_cat"]
    h_ini, h_fin = FRANJAS[st.session_state["hist_franja"]]
    r = resumen_historico(store_f, cat_f, str(d_ini), str(d_fin), h_ini, h_fin)
    if r["unidades"] == 0:
        st.warning("No hay ventas registradas para la combinación de filtros seleccionada (RNF-02).")
        return
    alcance = store_f or "las 3 sucursales"
    lider = r["tiendas"][0]
    dias_total = (max_d - min_d).days + 1
    cv = r["uds_ticket_std"] / max(0.01, r["uds_ticket"])
    estabilidad = "Alta estabilidad" if cv < 0.06 else ("Estabilidad media" if cv < 0.12 else "Variable")

    html(
        f"""
        <div class="grid-4">
          <div class="kpi" style="min-height:0;"><div>
            <div class="kpi-top"><span class="kpi-label">Unidades vendidas</span>{icon('assignment_turned_in', 24, '#7B5641')}</div>
            <div class="kpi-value">{r['unidades']:,d}</div>
            <div class="row small" style="gap:14px;margin-top:4px;font-size:13.5px;"><span style="color:#72856B;font-weight:500;">{r['dias']} días<br>auditados</span><span>• {alcance}</span></div></div>
            <div class="bar"><div style="width:{r['dias'] / dias_total * 100:.0f}%;background:#7B5641;"></div></div></div>
          <div class="kpi" style="min-height:0;"><div>
            <div class="kpi-top"><span class="kpi-label">Transacciones (tickets)</span>{icon('receipt_long', 24, '#7B5641')}</div>
            <div class="kpi-value">{r['tickets']:,d}</div>
            <div class="small" style="font-size:13.5px;margin-top:4px;">{r['tickets_dia']:,d} tickets/día • Ingreso ${r['importe']:,.0f}</div></div>
            <div class="bar"><div style="width:{r['tickets'] / len(tx) * 100:.0f}%;background:#22140D;"></div></div></div>
          <div class="kpi" style="min-height:0;"><div>
            <div class="kpi-top"><span class="kpi-label">Ratio uds / transacción</span>{icon('shopping_basket', 24, '#7B5641')}</div>
            <div class="kpi-value">{r['uds_ticket']:.2f}<span class="kpi-unit">uds/tkt</span></div>
            <div class="small" style="font-size:13.5px;margin-top:4px;"><span style="color:#72856B;font-weight:500;">{estabilidad}</span> • Desv. ±{r['uds_ticket_std']:.2f}</div></div>
            <div class="bar"><div style="width:{max(5, 100 - cv * 400):.0f}%;background:#72856B;"></div></div></div>
          <div class="kpi" style="min-height:0;"><div>
            <div class="kpi-top"><span class="kpi-label">Sucursal líder en volumen</span>{icon('workspace_premium', 24, '#7B5641')}</div>
            <div class="kpi-value sans" style="font-size:22px;margin-top:10px;line-height:28px;">{lider['sucursal']}</div>
            <div class="row small" style="gap:14px;margin-top:4px;font-size:13.5px;"><span class="mono" style="color:#7B5641;">{lider['unidades']:,d}<br>uds</span><span>({lider['share']:.1f}% del volumen total)</span></div></div>
            <div class="bar"><div style="width:{lider['share']:.0f}%;background:#7B5641;"></div></div></div>
        </div>
        """
    )

    # ---------------- serie temporal ----------------
    df_f = tx[(tx["fecha_dt"] >= pd.to_datetime(d_ini)) & (tx["fecha_dt"] <= pd.to_datetime(d_fin)) & (tx["hora"] >= h_ini) & (tx["hora"] <= h_fin)]
    if cat_f:
        df_f = df_f[df_f["product_category"] == cat_f]
    df_s = df_f[df_f["store_location"] == store_f] if store_f else df_f
    daily = df_s.groupby("fecha_dt", as_index=False).agg(unidades_vendidas=("transaction_qty", "sum")).sort_values("fecha_dt")
    daily["fecha"] = daily["fecha_dt"].dt.strftime("%Y-%m-%d")
    daily["media_7d"] = daily["unidades_vendidas"].rolling(7, min_periods=1).mean()
    n = min(30, max(1, len(daily) // 2))
    ini, fin = daily["unidades_vendidas"].head(n).mean(), daily["unidades_vendidas"].tail(n).mean()
    crec = (fin - ini) / ini * 100 if ini else 0.0
    fmin, fmax = daily.loc[daily["unidades_vendidas"].idxmin()], daily.loc[daily["unidades_vendidas"].idxmax()]
    with st.container(key="card_serie_hist"):
        html(
            f"""<div class="between" style="align-items:flex-start;border-bottom:1px solid #E9E7E0;padding-bottom:14px;">
            <div><div class="eyebrow">Serie temporal • {alcance}</div><div class="h3" style="font-size:20px;margin-top:4px;">Evolución de ventas diarias ({_fc(d_ini)} - {_fc(d_fin)} 2023)</div>
            <p class="p">Volumen diario observado y media móvil de 7 días en el rango y franja seleccionados.</p></div>
            <div class="row p" style="gap:18px;color:#1B1C18;"><span class="row" style="gap:6px;"><span class="dot" style="background:#22140D;width:10px;height:10px;"></span>Volumen diario</span>
            <span class="row" style="gap:6px;"><span style="width:14px;height:2px;background:#7B5641;display:inline-block;"></span>Media móvil (7d)</span></div></div>"""
        )
        fig = plot_historico_evolucion_semestral(daily)
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
        html(
            f"""<div class="between" style="border-top:1px solid #E9E7E0;padding-top:12px;flex-wrap:wrap;">
            <span class="mono p">Valle mínimo: {_fc(fmin['fecha_dt'])} ({fmin['unidades_vendidas']:,.0f} uds) • Pico máximo: {_fc(fmax['fecha_dt'])} ({fmax['unidades_vendidas']:,.0f} uds)</span>
            <span class="badge sq {'b-sage' if crec >= 0 else 'b-red'}" style="font-size:12px;">VARIACIÓN INICIO → FIN DEL RANGO: {crec:+.1f}%</span></div>
            <div class="small" style="margin-top:6px;">Partición del modelo: Train &lt; {meta.get('cutoff_date', '2023-06-01')} • Test ≥ {meta.get('cutoff_date', '2023-06-01')}</div>"""
        )

    # ---------------- estacionalidad + territorial ----------------
    tiendas_dow = [store_f] if store_f else ["Lower Manhattan", "Hell's Kitchen", "Astoria"]
    piv = (df_f[df_f["store_location"].isin(tiendas_dow)].groupby(["dia_semana", "store_location"])["transaction_qty"].sum()
           .unstack(fill_value=0).reindex(index=range(7), columns=tiendas_dow, fill_value=0))
    tot_dow = piv.sum(axis=1)
    mx = float(tot_dow.max()) or 1.0
    barras = []
    for d in range(7):
        segs = "".join(
            f'<div style="width:{piv.iloc[d][t] / mx * 100:.1f}%;background:{COLOR_TIENDA[i % 3] if len(tiendas_dow) > 1 else "#382820"};"></div>'
            for i, t in enumerate(tiendas_dow)
        )
        bold = "font-weight:700;color:#1B1C18;" if tot_dow.iloc[d] == mx else ""
        barras.append(
            f"""<div class="row" style="gap:14px;"><span class="small" style="width:34px;{bold}">{DIAS_C[d]}</span>
            <div style="flex:1;display:flex;height:26px;background:#F5F4ED;border-radius:2px;overflow:hidden;">{segs}</div>
            <span class="mono" style="width:70px;text-align:right;color:#1B1C18;">{tot_dow.iloc[d]:,.0f}</span></div>"""
        )
    d_max, d_min = DIAS_C[int(tot_dow.idxmax())], DIAS_C[int(tot_dow.idxmin())]
    share_finde = tot_dow.iloc[5:].sum() / max(1, tot_dow.sum()) * 100
    leyenda = "".join(
        f'<span class="row small" style="gap:6px;"><span style="width:12px;height:12px;background:{COLOR_TIENDA[i % 3]};border-radius:2px;display:inline-block;"></span>{t}</span>'
        for i, t in enumerate(tiendas_dow)
    )
    bloques = []
    for i, t in enumerate(r["tiendas"]):
        sel = store_f == t["sucursal"]
        bloques.append(
            f"""<div class="surface" style="padding:16px;{'outline:1px solid #C77C55;' if sel else ''}">
            <div class="between"><span class="row" style="gap:8px;font-size:17px;color:#1B1C18;">{icon(ICONO_TIENDA.get(t['sucursal'], 'store'), 22)}{t['sucursal']}</span>
            <span class="row" style="gap:10px;"><span class="mono" style="font-size:15px;color:#1B1C18;">{t['unidades']:,d} uds</span>
            <span class="badge sq {'b-peach-solid' if i == 0 else 'b-neutral'}">{t['share']:.1f}%</span></span></div>
            <div class="bar" style="height:9px;"><div style="width:{t['unidades'] / r['tiendas'][0]['unidades'] * 100:.1f}%;background:{COLOR_TIENDA[i % 3]};"></div></div>
            <div class="between mono small" style="margin-top:8px;"><span>{t['tickets']:,d} transacciones</span><span>{t['uds_ticket']:.2f} uds/ticket</span></div></div>"""
        )
    uds_t = [t["unidades"] for t in r["tiendas"]]
    dif = max(uds_t) - min(uds_t)
    balance = "Equilibrado" if dif / max(uds_t) < 0.05 else ("Moderado" if dif / max(uds_t) < 0.15 else "Desbalanceado")
    html(
        f"""
        <div class="grid-2">
          <div class="card" style="display:flex;flex-direction:column;">
            <div class="between" style="align-items:flex-start;"><div><div class="eyebrow">Estacionalidad semanal</div>
              <div class="h3" style="font-size:20px;margin-top:4px;">Demanda por día de la semana</div></div>{icon('view_week', 24, '#81756F')}</div>
            <div class="hr"></div>
            <p class="p" style="margin-bottom:16px;">Día de mayor volumen: <strong>{d_max}</strong>; menor: <strong>{d_min}</strong>. El fin de semana concentra el {share_finde:.1f}% de las unidades del filtro ({alcance}).</p>
            <div style="display:flex;flex-direction:column;gap:14px;">{''.join(barras)}</div>
            <div class="hr" style="margin-top:auto;"></div>
            <div class="between" style="flex-wrap:wrap;gap:10px;">{leyenda}<span class="mono small">Total: ~{tot_dow.sum() / 1000:.1f}k</span></div>
          </div>
          <div class="card" style="display:flex;flex-direction:column;">
            <div class="between" style="align-items:flex-start;"><div><div class="eyebrow">Desempeño territorial</div>
              <div class="h3" style="font-size:20px;margin-top:4px;">Comparativa de volumen por sucursal</div></div>{icon('storefront', 24, '#81756F')}</div>
            <div class="hr"></div>
            <p class="p" style="margin-bottom:16px;">Las 3 tiendas con el mismo filtro de categoría, fechas y franja. Liderazgo de <strong>{lider['sucursal']}</strong>.</p>
            <div style="display:flex;flex-direction:column;gap:14px;">{''.join(bloques)}</div>
            <div class="hr" style="margin-top:auto;"></div>
            <div class="between p"><span>Diferencial max-min: {dif:,d} uds</span><span>Balance operativo: {balance}</span></div>
          </div>
        </div>
        """
    )

    # ---------------- mix + curva intradía ----------------
    cats = r["categorias"]
    barra_mix = "".join(
        f'<div style="width:{c["share"]}%;background:{CATEGORY_COLORS.get(c["categoria"], "#D9D6CE")};" title="{c["categoria"]} {c["share"]}%"></div>'
        for c in cats
    )
    celdas = "".join(
        f"""<div><div class="row" style="gap:8px;font-weight:500;color:#1B1C18;"><span style="width:14px;height:14px;border-radius:2px;background:{CATEGORY_COLORS.get(c['categoria'], '#D9D6CE')};display:inline-block;"></span>{c['categoria']}</div>
        <div class="mono small" style="margin-top:4px;font-size:13px;">{c['share']:.1f}% • {c['unidades']:,d}<br>uds</div></div>"""
        for c in cats[:6]
    )
    uds_by = {c["categoria"]: c["unidades"] for c in cats}
    bebidas = sum(uds_by.get(k, 0) for k in ("Coffee", "Tea", "Drinking Chocolate"))
    ratio = f"{bebidas / uds_by['Bakery']:.1f} a 1" if uds_by.get("Bakery") else "n/d"
    top2 = cats[:2]
    mix_txt = (f"{top2[0]['categoria']} y {top2[1]['categoria']} representan conjuntamente el {top2[0]['share'] + top2[1]['share']:.0f}% del volumen expedido."
               if len(top2) == 2 else f"{top2[0]['categoria']} representa el 100% del volumen filtrado.")
    curva = r["curva_tickets_hora"]
    tv = [c["tickets"] for c in curva]
    ip = max(range(len(tv)), key=lambda i: tv[i])
    conc = sum(tv[max(0, ip - 1): ip + 2]) / max(1e-9, sum(tv)) * 100
    g4, g5 = st.columns(2, gap="medium")
    with g4:
        html(
            f"""<div class="card" style="height:100%;display:flex;flex-direction:column;">
            <div class="between" style="align-items:flex-start;"><div><div class="eyebrow">Mix de producto</div>
              <div class="h3" style="font-size:20px;margin-top:4px;">Participación por categoría</div></div>{icon('donut_large', 24, '#81756F')}</div>
            <div class="hr"></div><p class="p">{mix_txt}</p>
            <div style="display:flex;height:34px;border-radius:2px;overflow:hidden;margin:18px 0;">{barra_mix}</div>
            <div class="grid-3" style="gap:18px;">{celdas}</div>
            <div class="hr" style="margin-top:auto;"></div>
            <div class="between p"><span>Relación Bebida/Comida: {ratio}</span><span>Categorías analizadas: {len(cats)}</span></div></div>"""
        )
    with g5:
        with st.container(key="card_curva_hist"):
            html(
                f"""<div class="between" style="align-items:flex-start;"><div><div class="eyebrow">Ritmo operativo de servicio</div>
                <div class="h3" style="font-size:20px;margin-top:4px;">Curva de demanda horaria ({h_ini:02d}:00 - {h_fin:02d}:00)</div></div>{icon('schedule', 24, '#81756F')}</div>
                <div class="hr"></div><p class="p">Tickets promedio por hora en {alcance}. Pico en <strong>{curva[ip]['hora']}</strong>.</p>"""
            )
            st.plotly_chart(plot_historico_curva_intradia(curva), width="stretch", config={"displayModeBar": False})
            html(
                f"""<div class="hr"></div><div class="between"><span class="mono p">Concentración {curva[max(0, ip - 1)]['hora']}-{curva[min(len(curva) - 1, ip + 1)]['hora']}: {conc:.1f}%<br>tickets diarios</span>
                <span class="eyebrow" style="color:#72856B;">Tasa de flujo máxima: {max(tv):.0f}<br>tickets/hr</span></div>"""
            )

    # ---------------- tabla ----------------
    tabla = pd.DataFrame(cats)
    with st.container(key="card_tabla_hist"):
        a, b = st.columns([7.5, 2.5], vertical_alignment="center")
        with a:
            html(
                """<div class="eyebrow">Desglose exhaustivo</div><div class="h2" style="margin-top:4px;">Rendimiento por Categoría y Desempeño Operativo</div>
                <p class="p">Información consolidada directa del dataset Maven Coffee Shop Sales sin imputaciones artificiales.</p>"""
            )
        with b:
            st.download_button("Exportar CSV", tabla.to_csv(index=False).encode("utf-8-sig"), file_name="rendimiento_categorias.csv",
                               icon=":material/download:", width="stretch", key="hist_csv")
        filas = "".join(
            f"""<tr><td><span class="row" style="gap:10px;"><span class="dot" style="background:{CATEGORY_COLORS.get(c['categoria'], '#D9D6CE')};"></span>{c['categoria']}</span></td>
            <td class="num">{c['tickets']:,d}</td><td class="num" style="font-weight:600;">{c['unidades']:,d}</td><td class="num">${c['precio_prom']:.2f} USD</td>
            <td><span class="row" style="gap:8px;">{icon(ICONO_TIENDA.get(c['sucursal_lider'], 'store'), 18, '#7B5641')}{c['sucursal_lider']}<span class="mono small">({c['sucursal_lider_pct']:.1f}%)</span></span></td>
            <td style="text-align:center;"><span class="badge sq b-neutral">{_perfil_estacional(c['hora_pico'], c['categoria'])}</span></td></tr>"""
            for c in cats
        )
        html(
            f"""<div style="margin:6px -22px -20px -22px;"><table class="tbl"><thead><tr><th>Categoría</th><th class="r num">Transacciones</th>
            <th class="r num">Unidades<br>vendidas</th><th class="r num">Precio prom.<br>unitario</th><th>Sucursal líder</th><th style="text-align:center;">Perfil estacional</th></tr></thead>
            <tbody>{filas}</tbody><tfoot><tr><td>CONSOLIDADO<br>TOTAL</td><td class="num">{r['tickets']:,d}<br>tkts</td><td class="num">{r['unidades']:,d} uds</td>
            <td class="num">${r['precio_prom']:.2f} (Pond.)</td><td>{lider['sucursal']} (Total: {lider['share']:.1f}%)</td><td style="text-align:center;color:#72856B;">Periodo auditado</td></tr></tfoot></table>
            <div class="tbl-foot"><span class="mono">Mostrando {len(cats)} de {len(cats)} categorías registradas en el periodo</span>
            <span class="row" style="gap:8px;"><span class="eyebrow" style="font-size:10.5px;">Datos no normalizados</span><span class="dot" style="background:#4F4540;"></span><span style="color:#1B1C18;">Lectura directa del CSV Maven</span></span></div></div>"""
        )
