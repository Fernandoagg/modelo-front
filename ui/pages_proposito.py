"""Vista 'Propósito e Incorporación' (Figma: Main / Header).

Las secciones interactivas usan el modelo real:
- Simulador de tensión en barra: `predecir()` con el preset climático + perfil horario observado.
- Playground técnico: "Probar ping" mide la latencia real del contrato `predecir()`.
- Calculadora ROI: fórmula transparente con supuestos declarados (constantes abajo).
"""

from __future__ import annotations

import time
from typing import Any

import pandas as pd
import streamlit as st

from services.backend_bridge import (
    ejecutar_inferencia,
    load_transacciones,
    metricas_ganador,
    perfil_horario_real,
)
from ui.shell import ir_a
from ui.theme import ASSETS_DIR, badge, html, icon

# Supuestos de la calculadora ROI (calibrados para reproducir el escenario base del Figma: 3 sedes, 18 kg, 16%)
COSTO_EQ_USD_KG = 64.38        # USD por kg-equivalente de merma (café + lácteos + pan asociados)
REDUCCION_MERMA = 0.65         # reducción esperada de merma con pronóstico
HORAS_SEDE_ANIO = 91.3         # horas de barista reasignadas por sede/año
LICENCIA_SEDE_ANIO = 2158.0    # costo anual de operación por sede (USD)
IMPLEMENTACION_SEDE = 5000.0   # costo único de implementación por sede (USD)

PRESETS = {
    "Soleado": {"icon": "sunny", "temp": 24.0, "rain": 0.0, "sub": "24°C • Seco"},
    "Lluvia Torrencial": {"icon": "thunderstorm", "temp": 14.0, "rain": 90.0, "sub": "14°C • 90 mm"},
    "Ola de Calor": {"icon": "local_fire_department", "temp": 32.0, "rain": 0.0, "sub": "32°C • UV alto"},
}
HORAS_SIM = ["07:00", "07:30", "08:00", "08:30", "09:00", "09:30", "10:00", "10:30", "11:00"]
PASOS = {
    "01": ("Ingesta", "login", "Fuentes de Datos", "POS Maven (transacciones) + dataset climático estatal mensual por sucursal.",
           ("Pipeline src/data", "{n:,d} reg."), "Paso 01: Ingesta de Datos POS &amp; Clima Estatal",
           "Lectura de {n:,d} transacciones Maven (fecha, hora, sucursal, producto) y cruce con el clima mensual del estado asignado a cada tienda."),
    "02": ("Almacenamiento", "database", "Dataset procesado", "Matriz diaria sucursal × categoría con lags de 1/7/14 días y medias móviles.",
           ("dataset_limpio.csv", "0 nulos"), "Paso 02: Feature Engineering sin Fuga Temporal",
           "Rezagos con shift ≥ 1, variables cíclicas seno/coseno y medias móviles 7/14/28 días; escalado ajustado solo con Train."),
    "03": ("Inferencia", "memory", "CaféSmart Engine", "LightGBM Tweedie diario por categoría, expuesto vía el contrato predecir(entrada).",
           ("Inferencia < 50 ms", "MAE {mae:.2f} uds"), "Paso 03: Inferencia con el Contrato predecir()",
           "El frontend envía sucursal, categoría, fecha y clima; el backend devuelve unidades estimadas, banda al 85% y nivel de demanda."),
    "04": ("Barra activa", "devices", "Despacho en Tienda", "Dashboard Streamlit con alertas de stock, curvas horarias y guía de preparación.",
           ("Streamlit + Plotly", "Exportación CSV"), "Paso 04: Visualización Operativa en Barra",
           "Las 6 vistas consumen la misma inferencia: resumen del turno, pronóstico 7 días, recomendaciones y auditoría del modelo."),
}


def _ping() -> None:
    t0 = time.perf_counter()
    ejecutar_inferencia({"store_location": st.session_state["store_location"], "product_category": "Coffee",
                         "fecha": st.session_state["fecha_obj"].strftime("%Y-%m-%d"), "temp_media": 24.0, "precipitacion": 0.0})
    st.session_state["prop_ping_ms"] = (time.perf_counter() - t0) * 1000


def render(state: dict[str, Any]) -> None:
    tx = load_transacciones()
    n = len(tx)
    m = metricas_ganador()
    store = state["store_location"]
    fecha_str = state["fecha_str"]
    dow = int(pd.to_datetime(fecha_str).day_of_week)

    # ---------------- hero ----------------
    html(
        f"""
        <div class="card" style="padding:40px 44px;margin-top:6px;background:radial-gradient(circle at 85% 20%,#FCEEE6 0%,#FFFFFF 45%);">
          <div style="display:grid;grid-template-columns:1.25fr 2fr;gap:30px;align-items:end;">
            <div>
              <div class="row" style="gap:12px;align-items:flex-start;">
                <span class="badge sq b-neutral b-caps" style="white-space:normal;color:#7B5641;background:#F5F4ED;padding:8px 14px;line-height:18px;">
                  <span class="b-dot" style="background:#C77C55;"></span>Marco estratégico &amp;<br>incorporación interactiva</span>
                <span class="mono small" style="line-height:18px;">REV.<br>2023.06-NYC<br>• {n / 1000:.0f}K TICKETS</span></div>
              <h1 class="h1" style="font-size:40px!important;margin-top:16px!important;line-height:1.2!important;">Propósito del Proyecto &amp; Adopción de Negocio</h1>
              <p class="p" style="font-size:17px;line-height:30px;margin-top:10px;">CaféSmart AI resuelve la fricción operativa entre el tostado de precisión,
              la rotación de insumos perecederos y los picos de afluencia en cafeterías de especialidad mediante modelado probabilístico de demanda multi-variable.
              Experimenta cómo reacciona la barra en tiempo real.</p>
            </div>
            <div class="grid-2" style="gap:20px;">
              <div class="surface row" style="gap:18px;padding:20px 22px;border:1px solid #E9E7E0;"><span style="background:#22140D;border-radius:6px;padding:10px;">{icon('verified', 26, '#FFFFFF')}</span>
                <div><div class="eyebrow">Estatus piloto</div><div style="font-size:21px;color:#1B1C18;">Calibración Activa</div></div></div>
              <div class="surface row" style="gap:18px;padding:20px 22px;border:1px solid #E9E7E0;"><span style="background:#7B5641;border-radius:6px;padding:10px;">{icon('grid_view', 26, '#FFFFFF')}</span>
                <div><div class="eyebrow">Base entrenamiento</div><div class="mono" style="font-size:21px;color:#1B1C18;">{n:,d} transacciones</div></div></div>
            </div>
          </div>
        </div>
        """
    )

    # ---------------- simulador ----------------
    with st.container(key="card_simulador"):
        html(
            f"""<div class="between" style="align-items:flex-end;flex-wrap:wrap;border-bottom:1px solid #E9E7E0;padding:10px 0 18px 0;gap:14px;">
            <div><div class="row" style="gap:12px;">{badge('Simulador de tensión en barra en vivo', 'amber', dot=True).replace('badge', 'badge b-caps')}
            <span class="small" style="font-weight:600;letter-spacing:.06em;">Prueba de Estrés Dinámica</span></div>
            <h2 class="h1" style="font-size:36px!important;margin-top:10px!important;">Experimenta el Impacto en Turno en Vivo</h2></div>
            <p class="p" style="font-size:17px;max-width:620px;color:#81756F;">Ajusta clima y hora para ver el quiebre empírico vs la anticipación algorítmica (modelo real sobre {store}).</p></div>"""
        )
        izq, der = st.columns([1, 1.2], gap="medium")
        with izq:
            with st.container(key="surface_sim_izq"):
                html('<div class="h3" style="font-size:24px;">Variables de Entorno Exógenas</div><div class="eyebrow" style="margin-top:6px;">Condición climática (escenario simulado)</div>')
                preset = st.segmented_control(
                    "Clima",
                    list(PRESETS),
                    default="Soleado",
                    format_func=lambda p: f":material/{PRESETS[p]['icon']}: {p}",
                    key="prop_preset",
                    label_visibility="collapsed",
                    width="stretch",
                ) or "Soleado"
                html(f'<div class="mono small" style="text-align:center;">{" • ".join(f"{k}: {v["sub"]}" for k, v in PRESETS.items())}</div>')
                hora = st.select_slider("Bloque horario de apertura", HORAS_SIM, value="08:30", key="prop_hora")
                html(f'<div class="between mono small"><span>07:00<br>(Apertura)</span><span>08:30<br>(Rush hour)</span><span>10:00<br>(Mediodía)</span><span>11:00<br>(Cambio turno)</span></div>')

        p = PRESETS[preset]
        res = ejecutar_inferencia({"store_location": store, "product_category": "Coffee", "fecha": fecha_str,
                                   "temp_media": p["temp"], "precipitacion": p["rain"]})
        pred_dia, ref_dia = res["unidades_estimadas"], res["ref_historica_dow"]
        perfil = perfil_horario_real(store, "Coffee", dow)
        h_int = int(hora[:2])
        share = float(perfil.loc[perfil["hora_int"] == h_int, "share"].iloc[0])
        demanda_h = pred_dia * share
        gap = (pred_dia - ref_dia) / ref_dia if ref_dia else 0.0
        riesgo = max(8.0, min(92.0, 28 + abs(gap) * 140 + share * 120))
        garantia = max(80.0, 100 - m["wape"] * 0.155)
        merma_emp = abs(pred_dia - ref_dia) * 0.0185 * 4 + pred_dia * 0.0185 * 0.06
        merma_ai = pred_dia * 0.0185 * (m["wape"] / 100) * 0.12
        if preset == "Lluvia Torrencial":
            insight, accion = (f"Lluvia a las {hora} hrs: sube la preferencia por bebidas calientes con leche; el modelo proyecta {pred_dia:.0f} cafés en el día ({gap:+.0%} vs. referencia).",
                               "Turno: precalentar vaporizadores y reforzar leche entera")
        elif preset == "Ola de Calor":
            insight, accion = (f"Calor a las {hora} hrs: se desplaza demanda hacia bebidas frías; el modelo proyecta {pred_dia:.0f} cafés ({gap:+.0%} vs. referencia).",
                               "Turno: preparar cold brew y hielo con 1 h de anticipación")
        else:
            insight, accion = (f"Mañana templada a las {hora} hrs: balance parejo entre espresso en salón y vasos para llevar; {pred_dia:.0f} cafés proyectados ({gap:+.0%}).",
                               "Turno: mantener tolvas al 70% de capacidad")
        with izq:
            html(
                f"""<div style="background:#fff;border:1px solid #E9E7E0;border-radius:6px;padding:14px 16px;" class="row p">{icon('psychology', 22, '#7B5641')}<span>{insight}</span></div>
                <div class="between mono small" style="margin-top:12px;"><span>Simulación paramétrica<br>sobre {n / 1000:.0f}k tickets</span><span style="color:#7B5641;">● Actualizado al<br>instante</span></div>"""
            )
        with der:
            html(
                f"""
                <div class="surface" style="padding:22px;border:1px solid #E9E7E0;">
                  <div class="between"><span class="eyebrow">Comparativa de desempeño en vivo</span><span class="badge sq" style="background:#fff;border:1px solid #E9E7E0;">{icon('bolt', 16, '#C77C55')} En vivo</span></div>
                  <div class="grid-2" style="gap:14px;margin-top:14px;">
                    <div class="card" style="padding:18px;">
                      <div class="row eyebrow red" style="gap:6px;">{icon('cancel', 20, '#BA1A1A')}Método empírico<br>(ojímetro)</div>
                      <div class="between p" style="margin-top:12px;"><span>Riesgo quiebre stock</span><span class="mono" style="color:#BA1A1A;">{riesgo:.0f}%</span></div>
                      <div class="bar"><div style="width:{riesgo:.0f}%;background:#BA1A1A;"></div></div>
                      <div style="background:#FBE9E6;border:1px solid #F3C9C2;border-radius:4px;padding:12px;margin-top:14px;">
                        <div style="color:#BA1A1A;font-weight:600;">Preparación con promedio fijo</div>
                        <div class="p" style="font-size:13.5px;">El barista prepara para {ref_dia:.0f} cafés (promedio habitual) sin considerar el clima; la tolva puede agotarse en el pico de las {hora}.</div></div>
                      <div class="between p" style="margin-top:16px;"><span>Merma de café<br>estimada:</span><span class="mono" style="color:#BA1A1A;">{merma_emp:.1f} kg /<br>día</span></div>
                    </div>
                    <div class="card dark" style="padding:18px;">
                      <div class="between"><span class="row eyebrow" style="gap:6px;color:#F2E6DF;">{icon('check_circle', 20, '#F2E6DF')}Con CaféSmart AI</span><span class="badge sq" style="background:#4A3A32;color:#E8DCD5;">Optimizado</span></div>
                      <div class="between" style="margin-top:12px;color:#E8DCD5;font-size:14px;"><span>Garantía disponibilidad</span><span class="mono" style="color:#D8E8CF;">{garantia:.1f}%</span></div>
                      <div class="bar" style="background:#4A3A32;"><div style="width:{garantia:.0f}%;background:#D8E8CF;"></div></div>
                      <div style="background:#3A2C25;border:1px solid #57463D;border-radius:4px;padding:12px;margin-top:14px;">
                        <div style="font-weight:600;color:#fff;">Molienda pre-calibrada con buffer</div>
                        <div style="font-size:13.5px;color:#D9CBC3;line-height:19px;">Molienda pesada por adelantado para {demanda_h:.0f} cafés/hora proyectados a las {hora} (banda 85%: {res['rango_estimado_85'][0]}–{res['rango_estimado_85'][1]} en el día).</div></div>
                      <div class="between" style="margin-top:16px;color:#E8DCD5;font-size:14px;"><span>Merma de café<br>controlada:</span><span class="mono" style="color:#D8E8CF;">{merma_ai:.1f} kg /<br>día</span></div>
                    </div>
                  </div>
                  <div class="hr" style="margin-top:22px;"></div>
                  <div class="between" style="gap:14px;"><span class="eyebrow">Acción recomendada<br>inmediata:</span>
                    <span style="background:#fff;border:1px solid #E9E7E0;border-radius:4px;padding:8px 12px;font-size:14px;color:#1B1C18;">{accion}</span></div>
                  <div class="mono" style="color:#7B5641;margin-top:10px;">Demanda proyectada: {demanda_h:.0f} cafés / hora ({preset} ({p['temp']:.0f}°C))</div>
                  <div class="small" style="margin-top:6px;">Riesgo, merma y garantía son estimaciones ilustrativas derivadas de la predicción real y del error del modelo (WAPE {m['wape']:.2f}%).</div>
                </div>
                """
            )

    # ---------------- antes vs después ----------------
    with st.container(key="card_antes"):
        a, b = st.columns([6, 4], vertical_alignment="center")
        with a:
            html('<div class="eyebrow brown">Contraste operativo realista</div><div class="h2" style="font-size:26px;margin-top:4px;">El Turno en Barra: Antes vs Con CaféSmart AI</div>')
        with b:
            modo = st.segmented_control("Modo", ["Antes: Caos Empírico", "Después: Con CaféSmart AI"], default="Antes: Caos Empírico",
                                        key="prop_antes", label_visibility="collapsed", width="stretch") or "Antes: Caos Empírico"
        if modo.startswith("Antes"):
            col, cards = "#BA1A1A", [
                ("06:15 AM • Apertura", "warning", "Incertidumbre en Tolvas", "El barista líder prepara a ciegas 6 galones de batch brew. Llueve inesperadamente, la gente pide flat whites calientes y 4 litros de café terminado terminan en la tarja a mediodía.", "Pérdida en drenaje:", "-$42.00 USD/turno"),
                ("09:00 AM • Pico de servicio", "hourglass_empty", "Quiebre Inesperado", "Fila de 18 clientes. Se agotan los croissants frescos y la leche de almendra. El barista abandona la máquina de espresso para buscar cajas a la bodega, aumentando el tiempo de espera.", "Tiempo espera cliente:", "8 min 45 seg (+120%)"),
                ("19:30 PM • Cierre de caja", "delete", "Registro de Merma Manual", "Hojas arrugadas con anotaciones ilegibles. No hay correlación entre el café gastado y el dinero en POS. La dirección asume el 18% de desperdicio como \"costo natural del negocio\".", "Merma semanal no justificada:", "21.4% de compras"),
            ]
        else:
            col, cards = "#72856B", [
                ("06:15 AM • Apertura", "check_circle", "Batch Calibrado por Pronóstico", f"El turno arranca con la cantidad sugerida por el modelo ({state['last_prediction']['unidades_estimadas']:.0f} uds de {state['last_prediction']['categoria']} hoy) y ajustada por el clima del escenario.", "Desviación esperada:", f"± WAPE {m['wape']:.1f}%"),
                ("09:00 AM • Pico de servicio", "bolt", "Pico Anticipado", "La curva horaria observada indica a qué hora llega el pico; la vitrina y la leche se reponen 30 minutos antes de la fila.", "Hora pico prevista:", f"{perfil.loc[perfil['share'].idxmax(), 'hora']} hrs"),
                ("19:30 PM • Cierre de caja", "fact_check", "Cierre con Datos", "La guía de preparación se exporta a CSV y se contrasta con las ventas del día para medir la merma real por categoría.", "Exportación:", "CSV por turno"),
            ]
        html(
            '<div class="grid-3" style="margin-top:6px;">'
            + "".join(
                f"""<div class="surface" style="padding:20px 22px;border:1px solid #E9E7E0;display:flex;flex-direction:column;">
                <div class="between"><span class="eyebrow" style="color:{col};">{t}</span>{icon(ic, 22, col)}</div>
                <div class="h3" style="font-size:22px;margin:10px 0 6px 0;font-weight:500;">{h}</div><p class="p" style="font-size:15px;line-height:24px;">{d}</p>
                <div class="hr" style="margin-top:auto;"></div><div class="between p"><span>{fl}</span><span class="mono" style="color:{col};">{fv}</span></div></div>"""
                for t, ic, h, d, fl, fv in cards
            )
            + "</div>"
        )

    # ---------------- ROI ----------------
    with st.container(key="card_roi"):
        html(
            """<div class="between" style="align-items:flex-end;flex-wrap:wrap;"><div><div class="eyebrow brown">Impacto financiero directo</div>
            <h2 class="h1" style="font-size:34px!important;margin-top:6px!important;">Calculadora de Retorno de Inversión y Ahorro</h2></div>
            <p class="p" style="font-size:16px;color:#81756F;">Mueve los controles según la escala de tu cafetería</p></div>"""
        )
        l, r = st.columns([1.45, 1], gap="medium")
        with l:
            with st.container(key="surface_roi"):
                suc = st.slider("Número de sucursales", 1, 20, 3, key="prop_suc")
                html('<div class="between mono small"><span>1 sede boutique</span><span>10 sedes medianas</span><span>20 sedes cadena</span></div>')
                kg = st.slider("Kg de café tostado por sucursal / día", 5, 60, 18, key="prop_kg")
                html('<div class="between mono small"><span>5 kg (Microbarra)</span><span>30 kg (Alto tránsito)</span><span>60 kg (Flagship)</span></div>')
                merma = st.slider("Merma actual estimada (café + lácteos + pan) %", 8, 30, 16, key="prop_merma")
                html('<div class="between mono small"><span>8% (Bajo)</span><span>16% (Promedio industria)</span><span>30% (Crítico)</span></div>')
        ahorro_mes = suc * kg * 30 * (merma / 100) * REDUCCION_MERMA * COSTO_EQ_USD_KG
        horas = suc * HORAS_SEDE_ANIO
        roi = (ahorro_mes * 12) / (suc * LICENCIA_SEDE_ANIO)
        payback = (suc * IMPLEMENTACION_SEDE) / (ahorro_mes * 12 / 52) if ahorro_mes else 0
        proy = pd.DataFrame([{"sucursales": suc, "kg_dia_sucursal": kg, "merma_pct": merma, "ahorro_mensual_usd": round(ahorro_mes, 2),
                              "ahorro_anual_usd": round(ahorro_mes * 12, 2), "horas_barista_anio": round(horas), "roi_anualizado_x": round(roi, 1),
                              "payback_semanas": round(payback, 1), "supuesto_costo_usd_kg": COSTO_EQ_USD_KG, "supuesto_reduccion_merma": REDUCCION_MERMA}])
        with r:
            with st.container(key="dark_roi"):
                html(
                    f"""<div class="eyebrow" style="color:#E7CFC1;">Ahorro mensual proyectado</div>
                    <div class="row" style="align-items:baseline;gap:10px;"><span class="mono" style="font-size:44px;color:#fff;line-height:52px;">${ahorro_mes:,.0f}</span><span style="color:#E7CFC1;font-size:15px;white-space:nowrap;">USD / mes</span></div>
                    <p style="color:#D9CBC3;font-size:15px;margin:4px 0 0 0;">Calculado sobre reducción de merma del {REDUCCION_MERMA:.0%} y recuperación de ventas perdidas.</p>
                    <div style="height:1px;background:#57463D;margin:18px 0;"></div>
                    <div class="grid-2" style="gap:12px;">
                      <div style="background:#3A2C25;border-radius:4px;padding:14px;"><div style="color:#D9CBC3;font-size:13px;">HORAS BARISTA / AÑO</div><div class="mono" style="font-size:24px;color:#D8E8CF;white-space:nowrap;">{horas:,.0f} hrs</div><div style="color:#D9CBC3;font-size:13px;">Reasignadas a servicio</div></div>
                      <div style="background:#3A2C25;border-radius:4px;padding:14px;"><div style="color:#D9CBC3;font-size:13px;">ROI ANUALIZADO</div><div class="mono" style="font-size:24px;color:#FFDBCA;">{roi:.1f}x</div><div style="color:#D9CBC3;font-size:13px;">Payback en {payback:.0f} semanas</div></div>
                    </div>"""
                )
                st.download_button("Exportar Proyección Personalizada (CSV)", proy.to_csv(index=False).encode("utf-8"),
                                   file_name="proyeccion_roi_cafesmart.csv", icon=":material/download:", width="stretch", key="prop_roi_csv")

    # ---------------- playground técnico ----------------
    with st.container(key="card_playground"):
        html(
            f"""<div class="between" style="flex-wrap:wrap;border-bottom:1px solid #E9E7E0;padding-bottom:16px;">
            <div><div class="row" style="gap:10px;"><span class="eyebrow brown">Playground técnico</span><span class="small">● Haz clic en cada paso para ver la telemetría en vivo</span></div>
            <div class="h2" style="font-size:26px;margin-top:4px;">Arquitectura Integral del Ecosistema CaféSmart AI</div></div>
            <div class="row" style="gap:14px;">{badge('Pipeline local', 'neutral', dot=True).replace('b-neutral', 'b-neutral" style="background:#F5F4ED;color:#1B1C18;border:1px solid #E9E7E0;')}<span class="mono p">Latencia &lt; {max(50, state['store_summary']['tiempo_total_ms']):.0f}ms</span></div></div>"""
        )
        paso = st.segmented_control(
            "Paso",
            list(PASOS),
            default="01",
            format_func=lambda k: f"{k}. {PASOS[k][0]}",
            key="prop_paso",
            label_visibility="collapsed",
            width="stretch",
        ) or "01"
        tarjetas = []
        for k, (nombre, ic, titulo, desc, (f1, f2), _, _) in PASOS.items():
            activo = k == paso
            tarjetas.append(
                f"""<div class="surface" style="padding:20px;{'background:#fff;border:2px solid #7B5641;' if activo else ''}">
                <div class="between"><span class="eyebrow" style="color:{'#C77C55' if activo else '#7B5641'};">{k}. {nombre}</span>{icon(ic, 22, '#7B5641')}</div>
                <div class="h3" style="font-size:22px;font-weight:500;margin:10px 0 6px 0;">{titulo}</div><p class="p">{desc}</p>
                <div class="hr"></div><div class="between mono small"><span>{f1.format(n=n, mae=m['mae'])}</span><span style="color:#7B5641;">{f2.format(n=n, mae=m['mae'])}</span></div></div>"""
            )
        html('<div class="grid-4">' + "".join(tarjetas) + "</div>")
        _, _, _, _, _, det_t, det_d = PASOS[paso]
        with st.container(key="surface_paso"):
            d1, d2, d3 = st.columns([7, 2.2, 1.3], vertical_alignment="center")
            with d1:
                html(f'<div class="row" style="gap:14px;align-items:flex-start;"><span class="num-chip" style="background:#7B5641;font-size:14px;padding:8px 10px;">{paso}</span>'
                     f'<div><div class="h3" style="font-size:22px;font-weight:500;">{det_t}</div><div class="mono small" style="margin-top:4px;">{det_d.format(n=n)}</div></div></div>')
            with d2:
                ping = st.session_state.get("prop_ping_ms")
                html(f'<div style="background:#fff;border:1px solid #E9E7E0;border-radius:4px;padding:8px 12px;" class="mono small">'
                     f'{"Status: 200 OK • " + f"{ping:.1f} ms" if ping else "Status: listo • sin ping"}<br>predecir() local</div>')
            with d3:
                st.button("Probar ping", type="primary", on_click=_ping, width="stretch", key="prop_ping")

    # ---------------- ruta de implementación ----------------
    etapas = [
        ("1", "Semanas 1-2", "Ingesta y Normalización", f"Conexión con el data pipeline del sistema de caja (dataset POS Maven de {n / 1000:.0f}k registros entre Enero y Junio 2023).",
         ["Mapeo de recetas y gramajes por tipo de bebida.", "Cruce climático por sucursal (dataset estatal).", "Depuración de anomalías o tickets incompletos."], "Entregable técnico", "Warehouse Vectorizado Limpio", False),
        ("2", "Semanas 3-4", "Modelado y Calibración", "Benchmarking de precisión entre estimadores base ingenuos (mismo día semana anterior) y modelos de gradiente supervisado.",
         ["Horizonte diario por categoría con desagregación horaria.", "Evaluación MAE y WAPE sobre insumos clave.", "Umbrales dinámicos de seguridad de stock."], "Entregable técnico", f"Modelo Calibrado (WAPE {m['wape']:.1f}%)", False),
        ("3", "Semana 5 (Go-Live)", "Integración en Barra", "Despliegue de tableros de asistencia directa para baristas y encargados de turno durante los momentos clave del servicio.",
         ["Planificador de apertura (06:30 hrs): litros de batch brew.", "Alerta de reposición antes del pico de mediodía.", "Protocolo de horneado de pastelería escalonada."], "Entregable operativo", "Rutina de Barra Digitalizada", True),
        ("4", "Continuo", "Retroalimentación y Mermas", "Módulo de cierre donde el equipo registra el desperdicio medido físicamente (café purgado, leche agriada, pan no vendido).",
         ["Cruce diario: ventas vs consumo teórico de inventario.", "Atribución de causas de merma en un toque.", "Reentrenamiento semanal automatizado de pesos predictivos."], "Entregable de mejora", "Ciclo Cerrado de Control de Merma", False),
    ]
    html(
        """<div style="padding:30px 0 4px 0;"><div class="eyebrow brown">Ruta de implementación</div><h2 class="h1" style="font-size:34px!important;margin-top:6px!important;">Flujo de Adopción e Integración al Negocio</h2>
        <p class="subtitle" style="max-width:860px;">Cómo transiciona una sucursal desde el caos de pronósticos intuitivos hasta la sincronización automatizada en cuatro etapas estructuradas.</p></div>"""
        + '<div class="grid-4">'
        + "".join(
            f"""<div class="card" style="display:flex;flex-direction:column;{'border:2px solid #D9C4B8;' if dest else ''}">
            <div class="between"><span style="background:{'#FFDBCA' if dest else '#F5F4ED'};border-radius:50%;width:44px;height:44px;display:flex;align-items:center;justify-content:center;font-size:18px;">{num}</span>
            <span class="badge sq b-caps" style="background:{'#FFDBCA' if dest else '#F5F4ED'};color:#4F4540;">{sem}</span></div>
            <div class="h3" style="font-size:23px;margin:18px 0 8px 0;line-height:30px;">{tit}</div><p class="p" style="font-size:16px;line-height:26px;color:#81756F;">{desc}</p>
            <ul class="checks" style="margin:18px 0;">{''.join(f'<li>{icon("check", 18)}<span>{c}</span></li>' for c in checks)}</ul>
            <div class="surface" style="margin-top:auto;border:1px solid #E9E7E0;"><div class="eyebrow">{ent}</div><div class="h3" style="font-size:20px;font-weight:500;">{ent_v}</div></div></div>"""
            for num, sem, tit, desc, checks, ent, ent_v, dest in etapas
        )
        + "</div>"
    )

    # ---------------- matriz de valor ----------------
    kpis = [
        ("Reducción de merma", "trending_down", "-18.4%", "Insumos Críticos", "Reducción objetivo en desperdicio de leche fresca, alternativas vegetales y pastelería de vida útil corta (mismo día).", "Ahorro mensual est.:", "$1,420 USD / sucursal"),
        ("Disponibilidad peak", "verified", "+94.2%", "Tasa Cumplimiento", "Meta de stock activo en el pico matinal (07:30 - 10:30 hrs) en los 5 productos estrella, evitando roturas de stock visibles.", "Ventas recuperadas:", "+$2,890 USD / mes"),
        ("Eficiencia de turno", "timer", "15 min", "Ahorrados por Apertura", "Reducción del tiempo administrativo del barista líder en estimaciones matemáticas matutinas, enfocándose en calibración sensorial.", "Tiempo reasignado a calidad:", f"~{HORAS_SEDE_ANIO:.0f} hrs / año / sede"),
    ]
    impacto = [
        ("Café Tostado en Grano (Single-Origin &amp; Blend)", "Lotes fijos semanales sin considerar lluvia ni fines de semana largos.", "Pronóstico dinámico diario por perfil de tueste y rotación de tolvas.", "Frescura &lt; 21 días post-roast", "#1B1C18", "Eliminación de café rancio en stock"),
        ("Lácteos &amp; Bebidas Vegetales (Avena, Almendra)", "Pedidos a proveedores con 3 días fijos sin ajuste intradiario.", "Modelado de sustitución climática (frío = mayor leche caliente, calor = iced drinks).", "-21.5% merma por caducidad", "#C77C55", "Optimización de cámara frigorífica"),
        ("Batch Brew &amp; Cold Brew Prep", "Pre-preparación estándar de 6 galones por la mañana, sin correlación con clima.", "Recomendación de litros precisos por bloques horarios según sol o lluvia.", "-34% café preparado tirado al drenaje", "#1B1C18", "Máxima expresión aromática servida"),
        ("Panadería &amp; Repostería Artesanal", "Descongelado completo a las 06:00; excedente desechado a las 18:00 hrs.", "Horneado en 2 tandas guiado por alerta de tendencia a las 11:30 hrs.", "+12% margen bruto bollería", "#C77C55", "Producto tibio siempre disponible"),
    ]
    html(
        """<div class="between" style="padding:30px 0 4px 0;align-items:flex-end;"><div><div class="eyebrow brown">Impacto en cuenta de resultados</div>
        <div class="h2" style="font-size:28px;margin-top:6px;">Matriz de Valor y Retorno Esperado (KPIs Clave)</div></div><span class="mono p" style="color:#81756F;">Proyección anualizada por sucursal tipo (objetivos)</span></div>"""
        + '<div class="grid-3">'
        + "".join(
            f"""<div class="card" style="display:flex;flex-direction:column;"><div class="between"><span class="eyebrow">{lbl}</span>{icon(ic, 24, '#C77C55' if i == 0 else '#1B1C18')}</div>
            <div class="row" style="align-items:baseline;gap:10px;flex-wrap:wrap;margin-top:8px;"><span class="mono" style="font-size:46px;color:#22140D;line-height:56px;">{val}</span><span class="eyebrow brown" style="text-transform:none;font-size:15px;">{unit}</span></div>
            <p class="p" style="font-size:16px;line-height:26px;margin-top:8px;">{desc}</p>
            <div class="surface between" style="margin-top:auto;border:1px solid #E9E7E0;"><span class="p">{fl}</span><span class="mono" style="color:#1B1C18;">{fv}</span></div></div>"""
            for i, (lbl, ic, val, unit, desc, fl, fv) in enumerate(kpis)
        )
        + "</div>"
        + """<div class="tbl-wrap" style="margin-top:14px;"><div class="between" style="background:#F5F4ED;padding:20px 22px;"><span class="h3" style="font-size:22px;font-weight:500;">Matriz Detallada de Impacto por Categoría de Inventario</span>
        <span class="eyebrow">Horizontes de decisión</span></div><table class="tbl"><thead><tr><th>Categoría /<br>insumo</th><th>Método tradicional<br>(antes)</th><th>Con CaféSmart AI</th><th>Métrica de éxito<br>primaria</th><th class="r">Beneficio<br>operativo</th></tr></thead><tbody>"""
        + "".join(
            f"""<tr><td style="font-size:16px;">{a}</td><td class="small" style="font-size:14px;">{b}</td><td style="font-size:14.5px;">{c}</td>
            <td><span class="tag mono" style="color:{col};border:1px solid #E9E7E0;">{d}</span></td><td class="mono" style="text-align:right;font-size:14px;">{e}</td></tr>"""
            for a, b, c, d, col, e in impacto
        )
        + "</tbody></table></div>"
    )

    # ---------------- CTA ----------------
    with st.container(key="card_cta_prop"):
        a, b, c = st.columns([4.2, 2.4, 3.2], vertical_alignment="center")
        with a:
            html(
                f"""<div class="row" style="gap:18px;align-items:flex-start;"><span class="surface" style="padding:14px;border:1px solid #E9E7E0;">{icon('terminal', 28, '#1B1C18')}</span>
                <div><div class="h3" style="font-size:23px;line-height:30px;">¿Listo para inicializar la fase de calibración en barra?</div>
                <p class="p" style="font-size:16px;line-height:26px;">Puedes simular en vivo el comportamiento del motor con el dataset Maven Ene-Jun 2023 o descargar la guía técnica de integración.</p></div></div>"""
            )
        with b:
            st.button("Ejecutar Simulación Modelo", icon=":material/play_circle:", on_click=ir_a, args=("Pronóstico de demanda",), width="stretch", key="prop_cta_run")
        with c:
            pdf = ASSETS_DIR / "especificacion_tecnica_entrega2.pdf"
            if pdf.exists():
                st.download_button("Descargar Especificación Técnica (PDF)", pdf.read_bytes(), file_name="CafeSmart_AI_Especificacion_Tecnica.pdf",
                                   mime="application/pdf", icon=":material/description:", type="primary", width="stretch", key="prop_cta_pdf")
