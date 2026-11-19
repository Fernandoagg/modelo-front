"""Vista 'Estado de datos y modelo' (Figma: Main-9 / Header-9).

El layout replica el Figma; los estados reflejan la situación REAL del proyecto (Entrega 3: pipeline,
clima estatal mensual y modelo LightGBM ya entrenados y serializados), no los placeholders del mockup.
"""

from __future__ import annotations

from typing import Any

import streamlit as st

from services.backend_bridge import (
    STORE_STATE_MAP,
    cargar_importancia_variables,
    cargar_resultados_experimentos,
    cargar_resumen_experimentos,
    load_transacciones,
    metricas_ganador,
)
from src.config import WEATHER_FEATURES  # type: ignore  # noqa: E402
from ui.charts import plot_benchmark_modelos, plot_feature_importance
from ui.shell import ir_a
from ui.theme import badge, html, icon, page_header

VARIABLES_NATIVAS = ["transaction_id", "transaction_date", "transaction_time", "store_id", "store_location", "product_id",
                     "unit_price", "transaction_qty", "product_category", "product_type", "product_detail"]
COMPONENTES = [
    ("check_circle", "Ingesta de ventas Maven", "Data Engineering", "DISPONIBLE", "sage", "Pipeline reproducible `src/data` con limpieza y matriz diaria sin nulos."),
    ("check_circle", "Cruce climático estatal", "Data Engineering", "INTEGRADO", "sage", "Dataset mensual por estado (clima_mexico_estados.xlsx). Próximo: API diaria Open-Meteo."),
    ("check_circle", "Feature Engineering (Calendario + lags)", "Data Science", "DISPONIBLE", "sage", "Variables cíclicas seno/coseno, rezagos 1-14 días y medias móviles sin fuga temporal."),
    ("check_circle", "Benchmark de modelos (Baseline vs ML)", "Data Science", "VALIDADO", "sage", "8 experimentos con partición cronológica; ganador serializado en joblib."),
    ("pending", "Módulo de sugerencias de preparación", "Product / Dev", "PROTOTIPO UI LISTO", "peach-solid", "Validación en tienda con baristas y ajuste de márgenes por categoría."),
]


def render(state: dict[str, Any]) -> None:
    tx = load_transacciones()
    exps = cargar_resultados_experimentos()
    meta = cargar_resumen_experimentos()
    m = metricas_ganador()
    gan = next(e for e in exps if e["es_ganador"])
    base = next((e for e in exps if "Baseline" in e["experimento"]), gan)
    n_suc = tx["store_location"].nunique()
    candidatos = [e for e in exps if "Baseline" not in e["experimento"]]

    page_header(
        "Estado de datos y modelo",
        "Monitoreo de disponibilidad del dataset, variables climáticas y del modelo predictivo. Marco metodológico riguroso y transparente.",
        eyebrow=f"{icon('verified', 18)} Auditoría técnica &amp; trazabilidad",
        right=f"""<div class="surface row" style="gap:16px;padding:14px 20px;"><span class="dot" style="background:#7B5641;width:10px;height:10px;"></span>
              <span style="font-size:14px;color:#1B1C18;"><strong>Fase actual:</strong> Integración del modelo en<br>el dashboard (Entrega 4)</span>
              <span class="eyebrow row" style="gap:6px;"><span class="dot" style="background:#72856B;"></span>Modelo serializado<br>en producción local</span></div>""",
        divider=False,
    )

    html(
        f"""
        <div class="grid-4">
          <div class="kpi" style="min-height:0;"><div class="kpi-top"><span class="kpi-label">Transacciones listas</span>{icon('database', 22, '#1B1C18')}</div>
            <div class="kpi-value">{len(tx):,d}</div><div class="row p" style="gap:8px;margin-top:6px;"><span class="dot" style="background:#22140D;"></span>Ene - Jun 2023 (6 meses)</div></div>
          <div class="kpi" style="min-height:0;"><div class="kpi-top"><span class="kpi-label">Sucursales mapeadas</span>{icon('storefront', 22, '#1B1C18')}</div>
            <div class="kpi-value">{n_suc} / 3</div><div class="p" style="margin-top:6px;">{', '.join(STORE_STATE_MAP)}</div></div>
          <div class="kpi" style="min-height:0;"><div class="kpi-top"><span class="kpi-label">Covariables clima</span>{icon('partly_cloudy_day', 22, '#1B1C18')}</div>
            <div class="kpi-value">{len(WEATHER_FEATURES)} / {len(WEATHER_FEATURES)}</div><div class="row p" style="gap:8px;margin-top:6px;align-items:flex-start;"><span class="dot" style="background:#72856B;margin-top:6px;"></span>Temp. mín/media/máx, precipitación y amplitud térmica (estatal mensual)</div></div>
          <div class="kpi" style="min-height:0;"><div class="kpi-top"><span class="kpi-label">Modelos candidatos</span>{icon('account_tree', 22, '#1B1C18')}</div>
            <div class="kpi-value">{len(candidatos)} + Base</div><div class="row p" style="gap:8px;margin-top:6px;color:#7B5641;">{icon('tune', 18)} Partición cronológica (corte {meta.get('cutoff_date', '')})</div></div>
        </div>
        """
    )

    chips = "".join(f'<span class="tag mono">{v}</span>' for v in VARIABLES_NATIVAS)
    html(
        f"""
        <div class="grid-3">
          <div class="card" style="display:flex;flex-direction:column;gap:12px;">
            <div class="between" style="align-items:flex-start;flex-wrap:wrap;gap:8px;"><div class="row" style="align-items:flex-start;">{icon('receipt_long', 24)}<span class="h3" style="font-size:21px;">Datos de ventas</span></div>
              <span class="badge b-sage b-caps" style="white-space:normal;"><span class="b-dot"></span>Disponible • procesado</span></div>
            <p class="p" style="font-size:15px;">Base transaccional granular de punto de venta (POS) utilizada como verdad de terreno (Ground Truth).</p>
            <div class="surface"><div class="eyebrow">Fuente oficial</div><div style="font-size:16px;color:#1B1C18;">Maven Analytics — Coffee Shop Sales</div></div>
            <div class="grid-2" style="gap:10px;"><div class="surface"><div class="eyebrow">Periodo</div><div class="mono">01/01/2023 -<br>30/06/2023</div></div>
              <div class="surface"><div class="eyebrow">Volumen</div><div class="mono">{len(tx):,d}<br>registros</div></div></div>
            <div class="surface"><div class="eyebrow">Cobertura de red</div><div class="p" style="color:#1B1C18;">{n_suc} tiendas ({', '.join(STORE_STATE_MAP)})</div></div>
            <div class="surface"><div class="eyebrow">Variables nativas ({len(VARIABLES_NATIVAS)})</div><div style="display:flex;flex-wrap:wrap;gap:6px;margin-top:8px;">{chips.replace('class="tag mono"', 'class="tag mono" style="background:#EFEEE7;"')}</div></div>
            <div class="surface row p" style="align-items:flex-start;">{icon('check_circle', 20)}<span><strong style="color:#1B1C18;">Calidad verificada:</strong> sin valores nulos en claves primarias; matriz diaria por sucursal × categoría para el modelo.</span></div>
          </div>
          <div class="card" style="display:flex;flex-direction:column;gap:12px;">
            <div class="between" style="align-items:flex-start;flex-wrap:wrap;gap:8px;"><div class="row" style="align-items:flex-start;">{icon('cloud_sync', 24)}<span class="h3" style="font-size:21px;">Información climática</span></div>
              <span class="badge b-sage b-caps" style="white-space:normal;"><span class="b-dot"></span>Integrada (mensual)</span></div>
            <p class="p" style="font-size:15px;">Covariables para aislar el impacto de lluvia y temperatura en la demanda de bebidas frías vs. calientes.</p>
            <div class="surface"><div class="eyebrow">Fuente actual</div><div style="font-size:16px;color:#1B1C18;">Dataset climático estatal de México (mensual)</div></div>
            <div class="surface"><div class="eyebrow">Variables meteorológicas en el modelo</div>
              {''.join(f'<div class="between p" style="margin-top:6px;color:#1B1C18;"><span class="row" style="gap:6px;">{icon(i, 18)}{n}</span><span class="mono small">{u}</span></div>' for i, n, u in [('thermostat', 'Temperatura mínima', '°C'), ('device_thermostat', 'Temperatura media', '°C'), ('thermostat_auto', 'Temperatura máxima', '°C'), ('rainy', 'Precipitación acumulada', 'mm'), ('height', 'Amplitud térmica', '°C')])}</div>
            <div class="surface"><div class="eyebrow">Cruce sucursal → estado</div>
              {''.join(f'<div class="between p" style="margin-top:4px;color:#1B1C18;"><span>{k}</span><span class="mono small">{v}</span></div>' for k, v in STORE_STATE_MAP.items())}
              <div class="eyebrow" style="margin-top:10px;">Siguiente paso</div><div class="p" style="color:#1B1C18;">Sustituir el clima mensual por API diaria (Open-Meteo) para capturar eventos puntuales.</div></div>
            <div class="surface row p" style="align-items:flex-start;">{icon('info', 20)}<span><strong style="color:#1B1C18;">Nota de transparencia:</strong> la ablación sin clima obtuvo WAPE {next((e['wape_test'] for e in exps if not e.get('usa_clima', True) and 'Baseline' not in e['experimento']), 0):.2f}% vs {m['wape']:.2f}% con clima ({meta.get('weather_delta_wape_pp', 0):+.2f} pp): con granularidad mensual el aporte es marginal.</span></div>
          </div>
          <div class="card" style="display:flex;flex-direction:column;gap:12px;">
            <div class="between" style="align-items:flex-start;flex-wrap:wrap;gap:8px;"><div class="row" style="align-items:flex-start;">{icon('model_training', 24)}<span class="h3" style="font-size:21px;">Modelo de IA &amp; Validación</span></div>
              {badge('Entrenado', 'peach-solid', dot=True).replace('badge', 'badge b-caps')}</div>
            <p class="p" style="font-size:15px;">Estrategia de modelado predictivo basada en benchmarking comparativo sin atajos metodológicos.</p>
            <div class="surface"><div class="eyebrow">Baseline de control</div><div class="p" style="color:#1B1C18;"><strong>Naive estacional (t - 7):</strong> WAPE {base['wape_test']:.2f}% • MAE {base['mae']:.2f} uds.</div></div>
            <div class="surface"><div class="eyebrow">Modelos candidatos evaluados</div>
              <div class="grid-2" style="gap:6px 14px;margin-top:6px;">{''.join(f'<span class="row p" style="gap:6px;color:#1B1C18;"><span class="dot" style="background:#81756F;width:6px;height:6px;"></span>{e["modelo"].split(" (")[0]}</span>' for e in candidatos[:6])}</div></div>
            <div class="surface"><div class="eyebrow">Modelo ganador</div><div class="p" style="color:#1B1C18;"><strong>{gan['modelo']}</strong><br><span class="mono small">{gan['hiperparametros']}</span></div></div>
            <div class="surface"><div class="eyebrow">Métricas oficiales (test junio 2023)</div>
              <div style="display:flex;flex-wrap:wrap;gap:8px;margin-top:8px;">{''.join(f'<span class="tag mono" style="background:#fff;">{k}: {v}</span>' for k, v in [('WAPE', f"{m['wape']:.2f}%"), ('MAE', f"{m['mae']:.2f}"), ('RMSE', f"{m['rmse']:.2f}"), ('R²', f"{m['r2']:.4f}")])}</div></div>
            <div class="surface row p" style="align-items:flex-start;">{icon('science', 20)}<span><strong style="color:#1B1C18;">Mejora vs baseline:</strong> {meta.get('improvement_vs_baseline_pct', 0):.2f}% menos error (WAPE) con {meta.get('train_rows', 0):,d} muestras de entrenamiento y {meta.get('test_rows', 0):,d} de prueba.</span></div>
          </div>
        </div>
        """
    )

    # ---------------- benchmark + importancia ----------------
    b1, b2 = st.columns([1.15, 1], gap="medium")
    with b1:
        with st.container(key="card_bench"):
            html(f'<div class="eyebrow">Benchmark experimental (test set junio 2023)</div><div class="h3" style="font-size:20px;margin-top:4px;">WAPE (%) por experimento</div>')
            st.plotly_chart(plot_benchmark_modelos(exps), width="stretch", config={"displayModeBar": False})
    with b2:
        with st.container(key="card_imp"):
            html(f'<div class="eyebrow">Explicabilidad</div><div class="h3" style="font-size:20px;margin-top:4px;">Top 10 variables influyentes ({gan["modelo"]})</div>')
            st.plotly_chart(plot_feature_importance(cargar_importancia_variables()), width="stretch", config={"displayModeBar": False})

    # ---------------- matriz de componentes ----------------
    with st.container(key="card_matriz"):
        a, b = st.columns([7, 3], vertical_alignment="center")
        with a:
            html(
                f"""<div class="row" style="gap:10px;">{icon('table_chart', 24)}<span class="h2">Matriz de componentes del sistema</span></div>
                <p class="p" style="margin-top:4px;">Desglose funcional de tuberías de ingeniería de datos, modelado estadístico e interfaz operativa.</p>"""
            )
        with b:
            filtro = st.segmented_control("Filtro de vista", [f"Todos ({len(COMPONENTES)})", "En curso"], default=f"Todos ({len(COMPONENTES)})",
                                          key="estado_filtro", width="stretch") or "Todos"
        comps = COMPONENTES if filtro.startswith("Todos") else [c for c in COMPONENTES if c[4] != "sage"]
        filas = "".join(
            f"""<tr><td><span class="row" style="gap:10px;font-size:15px;">{icon(i, 22)}{n}</span></td><td><span class="tag mono">{r}</span></td>
            <td><span class="badge b-{v} b-caps"><span class="b-dot"></span>{e}</span></td><td class="p" style="font-size:15px;">{h.replace('`', '')}</td></tr>"""
            for i, n, r, e, v, h in comps
        )
        html(
            f"""<table class="tbl" style="margin-top:10px;"><thead><tr><th>Componente</th><th>Responsable / módulo</th><th>Estado actual</th><th>Próximo hito técnico</th></tr></thead>
            <tbody>{filas}</tbody></table>"""
        )

    with st.container(key="surface_compromiso"):
        a, b = st.columns([7.4, 2.6], vertical_alignment="center")
        with a:
            html(
                f"""<div class="row" style="gap:10px;">{icon('balance', 24)}<span class="h3" style="font-size:20px;">Compromiso de Honestidad Intelectual y Gobernanza</span></div>
                <p class="p" style="font-size:15px;line-height:23px;margin-top:6px;">CaféSmart AI rechaza métricas sintéticas ficticias. Este dashboard muestra el estado real: datos históricos verificados,
                clima estatal mensual integrado y un modelo validado con partición cronológica estricta.</p>"""
            )
        with b:
            st.button("Explorar módulo de pronóstico", icon=":material/arrow_forward:", icon_position="right", type="primary",
                      on_click=ir_a, args=("Pronóstico de demanda",), width="stretch", key="estado_go_pron")
