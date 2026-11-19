"""Vista 'Recomendaciones de inventario' (Figma: Main-7 / Header-7)."""

from __future__ import annotations

import re
from typing import Any

import pandas as pd
import streamlit as st

from services.backend_bridge import (
    CORE_CATEGORIES,
    generar_recomendaciones_turno,
    metricas_ganador,
    perfil_horario_real,
)
from ui.shell import SUCURSALES, bound
from ui.theme import badge, html, icon, img_src

ICONOS_PRODUCTO = {
    "Brewed Coffee - Dark Roast": "coffee_maker",
    "Barista Espresso Blend": "grain",
    "Croissant de Mantequilla": "bakery_dining",
    "Earl Grey Tea (Porciones)": "emoji_food_beverage",
    "Hot Chocolate Supreme": "local_cafe",
    "Bagel Clásico con Queso": "lunch_dining",
}
ICONOS_MOTIVO = ["trending_up", "autorenew", "schedule", "wb_twilight", "horizontal_rule", "light_mode"]


def _pct(texto: str) -> float:
    m = re.search(r"([+-]?\d+(?:\.\d+)?)%", texto)
    return float(m.group(1)) if m else 0.0


def _toggle_all(ids: list[str]) -> None:
    todos = all(st.session_state.get(f"chk_{i}", False) for i in ids)
    for i in ids:
        st.session_state[f"chk_{i}"] = not todos


def _sparkline(valores: list[float], w: int = 120, h: int = 34) -> str:
    if not valores or max(valores) <= 0:
        return ""
    mx = max(valores)
    pts = [(i * w / (len(valores) - 1), h - 4 - (v / mx) * (h - 8)) for i, v in enumerate(valores)]
    path = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    ix = max(range(len(valores)), key=lambda i: valores[i])
    return (
        f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}"><polyline fill="none" stroke="#7B5641" stroke-width="2" points="{path}"/>'
        f'<circle cx="{pts[ix][0]:.1f}" cy="{pts[ix][1]:.1f}" r="3.5" fill="#382820"/></svg>'
    )


def render(state: dict[str, Any]) -> None:
    store = state["store_location"]
    fecha_str = state["fecha_str"]
    resumen = state["store_summary"]
    fecha = pd.to_datetime(fecha_str)
    semana = fecha.isocalendar().week
    turno_corto = "Turno Matutino" if "Mañana" in state["turno"] else "Turno Vespertino"
    recs = generar_recomendaciones_turno(store, fecha_str, resumen["desglose"])
    margen_general = sum(_pct(r["margen_seguridad"]) for r in recs) / len(recs)
    m = metricas_ganador()

    # ---------------- hero ----------------
    html(
        f"""
        <div class="card" style="padding:26px 30px;background:linear-gradient(110deg,#FFFFFF 60%,#FDF3EE 100%);margin-top:6px;">
          <div class="between" style="align-items:flex-start;flex-wrap:wrap;">
            <div style="max-width:560px;flex:1 1 380px;">
              <div class="row" style="gap:8px;"><span class="eyebrow brown">Módulo de planificación</span><span class="mono small" style="color:#81756F;">• {turno_corto} • Sem. {semana}</span></div>
              <h1 class="h1" style="margin-top:8px!important;">Recomendaciones de inventario</h1>
              <p class="subtitle">Utiliza el pronóstico como apoyo para organizar la preparación y revisar productos prioritarios.</p>
            </div>
            <div class="surface row" style="padding:14px 20px;gap:18px;margin-top:30px;flex:0 0 auto;">
              <div style="text-align:right;"><div class="eyebrow">Margen estimado general</div>
                <div class="mono" style="font-size:20px;color:#1B1C18;line-height:28px;">+{margen_general:.1f}% seg.<br>sugerida</div></div>
              <span style="background:#FFDBCA;border-radius:8px;padding:8px;">{icon('tune', 24, '#7B5641')}</span>
            </div>
          </div>
          <div class="surface row p" style="margin-top:22px;padding:16px 20px;align-items:flex-start;line-height:24px;font-size:15px;">
            {icon('info', 20, '#4F4540')}<span><strong style="color:#1B1C18;">Cálculo orientativo:</strong> la cantidad para preparar suma la demanda
            estimada por el modelo más un margen de seguridad. El error de validación del modelo es WAPE {m['wape']:.2f}% (MAE {m['mae']:.2f} uds),
            por lo que los márgenes cubren la incertidumbre típica sin generar sobreproducción.</span>
          </div>
        </div>
        """
    )

    # ---------------- filtros ----------------
    with st.container(key="card_filtros_recs"):
        c1, c2, c3, c4 = st.columns([2.4, 2, 2.2, 3.4], vertical_alignment="bottom")
        with c1:
            bound(st.selectbox, "Sucursal de enfoque", "store_location", "w_store_recs", options=SUCURSALES)
        with c2:
            cat_f = st.selectbox("Categoría", ["Todas"] + CORE_CATEGORIES, key="recs_cat")
        with c3:
            prio_f = st.selectbox("Prioridad de revisión", ["Todos", "Revisado", "Pendiente de revisión", "Atención requerida"], key="recs_prio")

        ids = [r["id"] for r in recs]
        for r in recs:
            st.session_state.setdefault(f"chk_{r['id']}", r["checked_default"])

        def _estado(r: dict[str, Any]) -> str:
            return "Revisado" if st.session_state.get(f"chk_{r['id']}") else ("Atención requerida" if r["prioridad"] == "Atención requerida" else "Pendiente de revisión")

        visibles = [
            r for r in recs
            if (cat_f == "Todas" or r["categoria"] == cat_f) and (prio_f == "Todos" or _estado(r) == prio_f)
        ]
        guia = pd.DataFrame(
            [{"producto": r["producto"], "categoria": r["categoria"], "sucursal": r["sucursal"], "demanda_estimada": r["demanda_estimada"],
              "margen_seguridad": r["margen_seguridad"], "cantidad_sugerida": r["cant_sugerida"], "motivo": r["motivo"], "estado": _estado(r)}
             for r in visibles]
        )
        with c4:
            st.download_button("Exportar guía de preparación (CSV)", guia.to_csv(index=False).encode("utf-8"),
                               file_name=f"guia_preparacion_{store.replace(' ', '_')}_{fecha_str}.csv",
                               icon=":material/picture_as_pdf:", width="stretch", key="recs_csv")
        html(f'<div class="eyebrow row" style="gap:8px;margin-top:4px;"><span class="dot" style="background:#7B5641;"></span>Mostrando {len(visibles)} recomendaciones operativas</div>')

    # ---------------- 3 bloques ----------------
    desg = {d["categoria"]: d for d in resumen["desglose"]}
    by_id = {r["id"]: r for r in recs}
    tiles = [
        ("Brewed Coffee", "Lote Dark Roast", f"~{by_id['rec_1']['demanda_num']}", "tzs"),
        ("Espresso Blend", "Tolvas y molienda", f"{by_id['rec_2']['demanda_num']}", "kg"),
        ("Bakery / Viennoiserie", "Horneado previo", f"~{by_id['rec_3']['demanda_num'] + by_id['rec_6']['demanda_num']}", "uds"),
        ("Bebidas Calientes", "Bases y cacao", f"~{by_id['rec_5']['demanda_num']}", "porc"),
    ]
    tiles_html = "".join(
        f"""<div class="surface between" style="align-items:flex-start;padding:14px;"><div><div style="font-weight:600;font-size:14px;color:#1B1C18;">{a}</div>
        <div class="mono small" style="color:#81756F;">{b}</div></div><div class="mono" style="text-align:right;font-size:20px;color:#1B1C18;">{v}<div class="small">{u}</div></div></div>"""
        for a, b, v, u in tiles
    )
    estimado = sum(d["unidades_estimadas"] for d in resumen["desglose"] if d["categoria"] in CORE_CATEGORIES)
    recomendado = sum(d["unidades_recomendadas"] for d in resumen["desglose"] if d["categoria"] in CORE_CATEGORIES)
    cobertura = min(100.0, recomendado / max(1.0, estimado) * 100 - (100 - 96) * 0)
    perfil = perfil_horario_real(store, None, int(fecha.day_of_week))
    hora_ini = int(perfil[perfil["share"] > 0.02]["hora_int"].min())

    atipicos = sorted(
        [d for d in resumen["desglose"] if d["categoria"] in CORE_CATEGORIES and d["delta_pct_vs_ref"] > 0],
        key=lambda d: d["delta_pct_vs_ref"], reverse=True,
    )[:2]
    nombre_cat = {"Coffee": ("Dark Roast (Lote grande)", "coffee_maker"), "Bakery": ("Croissant de Mantequilla", "bakery_dining"),
                  "Tea": ("Earl Grey Tea", "emoji_food_beverage"), "Drinking Chocolate": ("Hot Chocolate Supreme", "local_cafe")}
    dias_pl = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábados", "domingos"]
    atip_html = "".join(
        f"""<div class="surface between" style="padding:14px;"><div class="row" style="gap:12px;">
        <span style="background:#fff;border-radius:6px;padding:6px;">{icon(nombre_cat[d['categoria']][1], 22, '#7B5641')}</span>
        <div><div style="font-weight:600;font-size:14px;color:#1B1C18;">{nombre_cat[d['categoria']][0]}</div>
        <div class="mono small" style="color:#C77C55;">{d['delta_pct_vs_ref']:+.1f}% vs. {dias_pl[fecha.day_of_week]} prom.</div></div></div>
        <div class="mono" style="color:#1B1C18;text-align:right;">{d['unidades_estimadas']:,.0f}<br>uds</div></div>"""
        for d in atipicos
    ) or '<div class="surface p">Sin categorías por encima de su media para esta fecha.</div>'
    max_delta = atipicos[0]["delta_pct_vs_ref"] if atipicos else 0.0
    html(
        f"""
        <div style="display:grid;grid-template-columns:1.25fr 1fr 0.8fr;gap:14px;">
          <div class="card" style="display:flex;flex-direction:column;">
            <div class="between"><span class="eyebrow row" style="gap:8px;"><span class="dot" style="background:#7B5641;"></span>Bloque 01</span>
              <span class="p" style="font-size:13.5px;">{state['turno']}</span></div>
            <div class="h3" style="font-size:20px;margin-top:10px;">Lotes / Preparaciones prioritarias sugeridas</div>
            <p class="p" style="margin:4px 0 14px 0;">4 categorías clave configuradas para arranque temprano de servicio según volumen pronosticado.</p>
            <div class="grid-2" style="gap:10px;">{tiles_html}</div>
            <div class="between p" style="margin-top:auto;padding-top:18px;"><span class="row" style="gap:6px;">{icon('hourglass_top', 20)} Comenzar extracción batch: {max(5, hora_ini - 1):02d}:45 AM</span>
              <span class="mono" style="color:#1B1C18;">{cobertura:.0f}%<br>Cobertura</span></div>
          </div>
          <div class="card" style="display:flex;flex-direction:column;">
            <div class="between"><span class="eyebrow row" style="gap:8px;"><span class="dot" style="background:#F2B9A0;"></span>Bloque 02</span>
              {badge(f'{max_delta:+.0f}% sobre media', 'peach-solid')}</div>
            <div class="h3" style="font-size:20px;margin-top:10px;">Productos con demanda atípica</div>
            <p class="p" style="margin:4px 0 14px 0;">{len(atipicos)} referencias proyectan concentración inhabitual de afluencia para este ciclo.</p>
            <div style="display:flex;flex-direction:column;gap:10px;">{atip_html}</div>
            <div class="between" style="margin-top:auto;padding-top:18px;"><span class="eyebrow">Perfil de afluencia<br>proyectada</span>{_sparkline(perfil['uds_promedio'].tolist())}</div>
          </div>
          <div class="card" style="display:flex;flex-direction:column;">
            <div class="between"><span class="eyebrow row" style="gap:8px;"><span class="dot" style="background:#81756F;"></span>Bloque 03</span>{icon('qr_code_2', 22, '#81756F')}</div>
            <div class="h3" style="font-size:20px;margin-top:10px;">Estado de cálculo de mermas</div>
            <div class="surface" style="margin-top:14px;"><div class="eyebrow">Diagnóstico de datos</div>
              <div class="p" style="color:#1B1C18;font-size:15px;">No aplicable — el dataset Maven no registra mermas ni existencias físicas de almacén.</div></div>
            <p class="p" style="margin-top:12px;">Las recomendaciones se apoyan exclusivamente en las transacciones de venta registradas, sin suponer existencias previas ni inventario descartado.</p>
            <div class="row small" style="margin-top:auto;padding-top:14px;gap:8px;">{icon('database', 18)} Alcance estrictamente transaccional</div>
          </div>
        </div>
        """
    )

    # ---------------- guía detallada ----------------
    calibrados = sum(1 for i in ids if st.session_state.get(f"chk_{i}"))
    pct = calibrados / len(ids) * 100
    with st.container(key="card_guia"):
        html(
            f"""<div class="between" style="background:#F5F4ED;margin:-20px -22px 0 -22px;padding:14px 22px;border-radius:8px 8px 0 0;flex-wrap:wrap;">
            <div class="row" style="gap:12px;"><span style="background:#FFDBCA;border-radius:50%;padding:6px;">{icon('task_alt', 20, '#7B5641')}</span>
            <strong style="font-size:15px;">Preparación matutina: {calibrados} de {len(ids)} insumos calibrados ({pct:.0f}%)</strong>
            {badge('En progreso • persiana ' + f'{max(5, hora_ini):02d}:00 AM', 'peach-solid').replace('badge', 'badge sq b-caps')}</div>
            <div class="row p" style="gap:12px;">{icon('timer', 20)} Faltan {len(ids) - calibrados} ítems por validar
            <div class="bar" style="width:180px;margin:0;height:8px;"><div style="width:{pct:.0f}%;background:#7B5641;"></div></div></div></div>"""
        )
        g1, g2, g3, g4 = st.columns([3, 2.4, 3.2, 1.6], vertical_alignment="center")
        with g1:
            html(f'<div class="row" style="gap:10px;">{icon("checklist", 24)}<span class="h3" style="font-size:20px;">Guía Detallada de Preparación para el Turno</span></div>')
        with g2:
            html('<span class="p">Marcar ítems validados durante apertura</span>')
        with g3:
            html(
                f"""<div class="row" style="background:#fff;border:1px solid #E9E7E0;border-radius:6px;padding:10px 14px;gap:14px;">
                <span class="dot" style="background:#7B5641;"></span><span class="eyebrow" style="color:#1B1C18;">Apertura de barra:</span>
                <span class="mono" style="color:#7B5641;">{calibrados} / {len(ids)} ({pct:.0f}%)</span>
                <div class="bar" style="width:70px;margin:0;height:8px;"><div style="width:{pct:.0f}%;background:#7B5641;"></div></div></div>"""
            )
        with g4:
            st.button("Alternar selección", type="tertiary", on_click=_toggle_all, args=(ids,), key="recs_toggle")

        cols_w = [2.6, 1.6, 1.5, 1.5, 1.8, 2.2, 1.9]
        heads = ["Producto o categoría", "Sucursal", "Demanda estimada", "Margen de seguridad", "Cant. orientativa sugerida", "Motivo de la recomendación", "Estado de revisión"]
        with st.container(key="surface_guia_head"):
            hc = st.columns(cols_w)
            for col, h in zip(hc, heads):
                with col:
                    html(f'<span class="eyebrow">{h}</span>')
        for idx, r in enumerate(visibles):
            with st.container(key=f"row_guia_{r['id']}"):
                rc = st.columns(cols_w, vertical_alignment="center")
                with rc[0]:
                    html(
                        f"""<div class="row" style="gap:10px;align-items:flex-start;"><span style="background:#F5F4ED;border-radius:4px;padding:4px;">{icon(ICONOS_PRODUCTO.get(r['producto'], 'inventory_2'), 20)}</span>
                        <div><div style="font-weight:600;font-size:14.5px;color:#1B1C18;">{r['producto']}</div><div class="eyebrow" style="font-size:10.5px;">{r['subtitulo']}</div></div></div>"""
                    )
                with rc[1]:
                    html(f'<span class="tag">{r["sucursal"]}</span>')
                with rc[2]:
                    html(f'<div class="mono" style="text-align:right;font-size:14.5px;">{r["demanda_estimada"]}</div>')
                with rc[3]:
                    html(f'<span class="row p" style="gap:6px;"><span class="dot" style="background:#81756F;width:4px;height:12px;border-radius:2px;"></span>{r["margen_seguridad"]}</span>')
                with rc[4]:
                    alerta = r["prioridad"] != "Revisado"
                    html(f'<div class="mono" style="text-align:right;background:{"#FCEEE6" if alerta else "#F5F4ED"};padding:6px 8px;border-radius:4px;color:{"#C77C55" if alerta else "#1B1C18"};">{r["cant_sugerida"]}<br><span style="font-size:12px;color:#81756F;">(orientativo)</span></div>')
                with rc[5]:
                    html(f'<span class="row p" style="gap:8px;align-items:flex-start;color:#1B1C18;">{icon(ICONOS_MOTIVO[idx % len(ICONOS_MOTIVO)], 18)}{r["motivo"]}</span>')
                with rc[6]:
                    k1, k2 = st.columns([1, 3], vertical_alignment="center")
                    with k1:
                        st.checkbox("validado", key=f"chk_{r['id']}", label_visibility="collapsed")
                    with k2:
                        est = _estado(r)
                        variant = "neutral" if est == "Revisado" else ("peach-solid" if est == "Atención requerida" else "neutral")
                        html(badge(est, variant))
        html(
            f"""<div class="between small" style="padding:14px 0 0 0;font-size:13.5px;"><span class="row" style="gap:8px;">{icon('verified_user', 18)}
            Recomendación adaptada a capacidad estándar de tolvas y hornos batch en {store}</span>
            <span>Última corrida analítica: {state['store_summary']['tiempo_total_ms']:.0f} ms • {fecha_str}</span></div>"""
        )

    # ---------------- tarjetas con foto ----------------
    fotos = [
        ("Insumo base de tueste", "Perfil de Grano Dark Roast",
         f"Verifica que las tolvas mantengan nivel constante previo a la apertura de las {max(5, hora_ini):02d}:00 AM para evitar descalibración en extracción continua.",
         "tueste_dark_roast.jpg"),
        ("Rotación en vitrina", "Precalentado de Panadería",
         f"La demanda matutina de croissants y bagels ({by_id['rec_3']['demanda_num'] + by_id['rec_6']['demanda_num']} uds estimadas) requiere horneado distribuido en 2 tandas para mantener frescura de corteza.",
         "panaderia_vitrina.jpg"),
        ("Control de calidad", "Alineación Barista en Turno",
         "El barista encargado debe cotejar los tickets emitidos contra estas pautas agregadas para reportar anomalías de consumo al fin de turno.",
         "barista_turno.jpg"),
    ]
    html(
        '<div class="grid-3">'
        + "".join(
            f"""<div class="card"><div class="eyebrow">{e}</div><div class="h3" style="font-size:20px;margin:6px 0 10px 0;">{t}</div>
            <p class="p" style="font-size:15px;line-height:23px;min-height:92px;">{d}</p><img class="img-card" src="{img_src(f)}" style="margin-top:14px;" alt=""></div>"""
            for e, t, d, f in fotos
        )
        + "</div>"
    )
    html(
        f"""<div class="surface row" style="align-items:flex-start;padding:18px 22px;gap:14px;border-radius:8px;">
        <span style="background:#EFEEE7;border-radius:6px;padding:6px;">{icon('assignment_late', 22, '#1B1C18')}</span>
        <div><div class="eyebrow" style="color:#1B1C18;">Aviso importante de operaciones</div>
        <p class="p" style="font-size:15px;line-height:23px;">Este módulo no sustituye el criterio del barista o encargado de tienda. Las cantidades de preparación son sugerencias basadas en patrones de demanda agregada del dataset histórico de ventas.</p></div></div>"""
    )
