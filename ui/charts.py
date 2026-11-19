"""Catálogo completo de gráficas interactivas en Plotly con el sistema visual de Figma CaféSmart AI."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
import plotly.graph_objects as go


def _apply_figma_layout(
    fig: go.Figure,
    height: int = 320,
    yaxis_title: str = "",
    xaxis_title: str = "",
    show_legend: bool = True,
    margin: dict[str, int] | None = None,
) -> go.Figure:
    """Aplica la estética editorial de alta fidelidad de Figma a cualquier figura Plotly."""
    fig.update_layout(
        height=height,
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        font=dict(family="Inter, sans-serif", color="#4F4540", size=12),
        margin=margin or dict(l=44, r=20, t=24, b=40),
        showlegend=show_legend,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1.0,
            bgcolor="rgba(245, 244, 237, 0.85)",
            bordercolor="#E4E3DC",
            borderwidth=1,
            font=dict(family="Inter, sans-serif", size=11.5, color="#1B1C18"),
        ),
        hovermode="x unified",
        hoverlabel=dict(
            bgcolor="#22140D",
            bordercolor="#382820",
            font=dict(family="JetBrains Mono, monospace", size=12, color="#FFFFFF"),
        ),
        xaxis=dict(
            title=dict(text=xaxis_title, font=dict(size=11, color="#81756F")),
            showgrid=False,
            linecolor="#E4E3DC",
            tickfont=dict(family="JetBrains Mono, monospace", size=10.5, color="#81756F"),
        ),
        yaxis=dict(
            title=dict(text=yaxis_title, font=dict(size=11, color="#81756F")),
            showgrid=True,
            gridcolor="#EFEEE7",
            gridwidth=1,
            griddash="dot",
            zeroline=False,
            linecolor="rgba(0,0,0,0)",
            tickfont=dict(family="JetBrains Mono, monospace", size=10.5, color="#81756F"),
        ),
    )
    return fig


def plot_resumen_demanda_horaria(df_horaria: pd.DataFrame) -> go.Figure:
    """Gráfica principal de Vista 1 (Resumen operativo): Demanda horaria 06:00 a 20:00 hrs."""
    fig = go.Figure()

    # Sombreado de Turno Mañana (06:00 a 14:00), igual que el selector "Jornada operativa"
    fig.add_vrect(
        x0="06:00",
        x1="14:00",
        fillcolor="rgba(245, 244, 237, 0.55)",
        layer="below",
        line_width=0,
    )

    # Banda de incertidumbre al 85%
    fig.add_trace(
        go.Scatter(
            x=pd.concat([df_horaria["hora"], df_horaria["hora"][::-1]]),
            y=pd.concat([df_horaria["rango_max"], df_horaria["rango_min"][::-1]]),
            fill="toself",
            fillcolor="rgba(250, 242, 238, 0.78)",
            line=dict(color="rgba(237, 212, 199, 0.5)", width=1),
            name="Rango de incertidumbre (85%)",
            hoverinfo="skip",
        )
    )

    # Histórico observado
    fig.add_trace(
        go.Scatter(
            x=df_horaria["hora"],
            y=df_horaria["historico_observado"],
            mode="lines+markers",
            name="Histórico observado",
            line=dict(color="#382820", width=2.5, shape="spline", smoothing=0.6),
            marker=dict(size=6, color="#382820"),
            hovertemplate="Histórico: <b>%{y:.1f} uds/h</b><extra></extra>",
        )
    )

    # Pronóstico proyectado
    fig.add_trace(
        go.Scatter(
            x=df_horaria["hora"],
            y=df_horaria["pronostico_proyectado"],
            mode="lines+markers",
            name="Pronóstico proyectado",
            line=dict(color="#C77C55", width=2.4, dash="dash", shape="spline", smoothing=0.6),
            marker=dict(size=7, color="#C77C55", line=dict(color="#FFFFFF", width=1.5)),
            hovertemplate="Pronóstico IA: <b>%{y:.1f} uds/h</b><extra></extra>",
        )
    )

    # Línea vertical divisoria de cambio de turno (14:00)
    fig.add_vline(
        x="14:00",
        line_width=1.5,
        line_dash="dash",
        line_color="#7B5641",
    )

    max_row = df_horaria.loc[df_horaria["pronostico_proyectado"].idxmax()]
    fig.add_annotation(
        x=max_row["hora"],
        y=float(max_row["pronostico_proyectado"]),
        text=f"Pico: ~{max_row['pronostico_proyectado']:.0f} uds/h",
        showarrow=True,
        arrowhead=2,
        arrowsize=1,
        arrowwidth=1.2,
        arrowcolor="#382820",
        ax=0,
        ay=-32,
        bgcolor="#382820",
        bordercolor="#382820",
        borderpad=4,
        font=dict(family="JetBrains Mono, monospace", size=10.5, color="#FFFFFF"),
    )

    fig.add_annotation(
        x="10:00",
        y=1.06,
        yref="paper",
        text="TURNO MAÑANA (06:00 - 14:00)",
        showarrow=False,
        font=dict(family="Inter, sans-serif", size=9.5, color="#7B5641"),
    )
    fig.add_annotation(
        x="17:00",
        y=1.06,
        yref="paper",
        text="TURNO TARDE (14:00 - 20:00)",
        showarrow=False,
        font=dict(family="Inter, sans-serif", size=9.5, color="#81756F"),
    )

    return _apply_figma_layout(fig, height=340, yaxis_title="Unidades / hora")


def plot_serie_temporal_pronostico(df_serie: pd.DataFrame) -> go.Figure:
    """Gráfica 1 del Catálogo (Vista 2 - Pronóstico de demanda): Serie histórica real vs pronóstico 7d + banda 85%."""
    fig = go.Figure()

    df_hist = df_serie[df_serie["tipo"] == "Histórico real"].copy()
    df_proj = df_serie[df_serie["tipo"] == "Pronóstico"].copy()

    # Conectar visualmente el último punto histórico con el primer punto de pronóstico
    if not df_hist.empty and not df_proj.empty:
        last_hist = df_hist.iloc[-1]
        bridge_row = pd.DataFrame(
            [
                {
                    "etiqueta": last_hist["etiqueta"],
                    "pronostico": last_hist["unidades_reales"],
                    "intervalo_min": last_hist["unidades_reales"],
                    "intervalo_max": last_hist["unidades_reales"],
                }
            ]
        )
        df_proj_plot = pd.concat([bridge_row, df_proj], ignore_index=True)
    else:
        df_proj_plot = df_proj

    # Banda de confianza al 85% en la zona de pronóstico
    if not df_proj_plot.empty:
        fig.add_trace(
            go.Scatter(
                x=pd.concat([df_proj_plot["etiqueta"], df_proj_plot["etiqueta"][::-1]]),
                y=pd.concat([df_proj_plot["intervalo_max"], df_proj_plot["intervalo_min"][::-1]]),
                fill="toself",
                fillcolor="rgba(199, 124, 85, 0.16)",
                line=dict(color="rgba(199, 124, 85, 0.32)", width=1),
                name="Intervalo confianza (85%)",
                hoverinfo="skip",
            )
        )

    # Serie histórica real
    fig.add_trace(
        go.Scatter(
            x=df_hist["etiqueta"],
            y=df_hist["unidades_reales"],
            mode="lines+markers",
            name="Histórico real",
            line=dict(color="#22140D", width=2.6, shape="spline", smoothing=0.45),
            marker=dict(size=7, color="#22140D", line=dict(color="#FFFFFF", width=1.5)),
            hovertemplate="Real observado: <b>%{y:,.1f} uds</b><extra></extra>",
        )
    )

    # Pronóstico del modelo LGBMRegressor (Tweedie)
    if not df_proj_plot.empty:
        fig.add_trace(
            go.Scatter(
                x=df_proj_plot["etiqueta"],
                y=df_proj_plot["pronostico"],
                mode="lines+markers",
                name="Pronóstico IA (LightGBM Tweedie)",
                line=dict(color="#C77C55", width=2.6, dash="dash", shape="spline", smoothing=0.45),
                marker=dict(size=8, color="#FFFFFF", line=dict(color="#C77C55", width=2.2)),
                hovertemplate="Pronóstico IA: <b>%{y:,.1f} uds</b><extra></extra>",
            )
        )

    # Anotación en el primer día pronosticado
    if not df_proj.empty:
        first_proj = df_proj.iloc[0]
        fig.add_annotation(
            x=first_proj["etiqueta"],
            y=float(first_proj["pronostico"]),
            text=f"{first_proj['etiqueta']}: {first_proj['pronostico']:,.0f} uds",
            showarrow=True,
            arrowhead=2,
            arrowcolor="#382820",
            ax=20,
            ay=-36,
            bgcolor="#FFFFFF",
            bordercolor="#E4E3DC",
            borderwidth=1,
            borderpad=5,
            font=dict(family="JetBrains Mono, monospace", size=11, color="#22140D"),
        )

    if not df_hist.empty:
        corte_label = df_hist.iloc[-1]["etiqueta"]
        fig.add_vline(
            x=corte_label,
            line_width=1.5,
            line_dash="dot",
            line_color="#7B5641",
        )
        fig.add_annotation(
            x=corte_label,
            y=1.05,
            yref="paper",
            text="PUNTO DE CORTE",
            showarrow=False,
            bgcolor="#382820",
            borderpad=3,
            font=dict(family="Inter, sans-serif", size=9.5, color="#FFFFFF"),
        )

    # Orden cronológico explícito: Plotly ordena categorías según la primera traza dibujada (la banda),
    # lo que dejaba los días históricos al final del eje.
    fig.update_xaxes(categoryorder="array", categoryarray=list(dict.fromkeys(df_serie["etiqueta"].tolist())))
    return _apply_figma_layout(fig, height=340, yaxis_title="Demanda (unidades/día)")


def plot_distribucion_categorias_proyectada(desglose: list[dict[str, Any]]) -> go.Figure:
    """Gráfica 2 del Catálogo (Entrega 2): Barras horizontales de Demanda Estimada vs Referencia por Categoría."""
    df_cat = pd.DataFrame(desglose).sort_values("unidades_estimadas", ascending=True)

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            y=df_cat["categoria"],
            x=df_cat["ref_historica_dow"],
            name="Referencia histórica (mismo día sem.)",
            orientation="h",
            marker=dict(color="#E4E3DC"),
            hovertemplate="Ref. histórica: <b>%{x:,.1f} uds</b><extra></extra>",
        )
    )
    fig.add_trace(
        go.Bar(
            y=df_cat["categoria"],
            x=df_cat["unidades_estimadas"],
            name="Pronóstico IA (unidades estimadas)",
            orientation="h",
            marker=dict(color="#382820"),
            text=[f"{v:,.1f} uds" for v in df_cat["unidades_estimadas"]],
            textposition="outside",
            textfont=dict(family="JetBrains Mono, monospace", size=10.5, color="#22140D"),
            hovertemplate="Pronóstico IA: <b>%{x:,.1f} uds</b><extra></extra>",
        )
    )

    fig = _apply_figma_layout(fig, height=340, xaxis_title="Volumen Estimado (unidades físicas/día)")
    fig.update_layout(barmode="group", yaxis=dict(showgrid=False))
    return fig


def plot_sensibilidad_clima(
    df_clean: pd.DataFrame,
    store_location: str,
    product_category: str,
    sim_temp: float,
    sim_rain: float,
    sim_pred: float,
) -> go.Figure:
    """Gráfica 3 del Catálogo (Entrega 2): Scatter Plot de Sensibilidad de la Demanda al Clima + Escenario Simulado."""
    df_sub = df_clean[df_clean["store_location"] == store_location].copy()
    if product_category != "Todas las categorías":
        df_sub = df_sub[df_sub["product_category"] == product_category]
    else:
        df_sub = (
            df_sub.groupby("fecha", as_index=False)
            .agg(
                unidades_vendidas=("unidades_vendidas", "sum"),
                temp_media=("temp_media", "first"),
                precipitacion=("precipitacion", "first"),
            )
        )

    # Añadir jitter horizontal leve para visualizar la densidad diaria sobre temperaturas mensuales
    rng = np.random.default_rng(42)
    temp_jitter = df_sub["temp_media"].to_numpy(dtype=float) + rng.normal(0, 0.45, size=len(df_sub))
    unidades = df_sub["unidades_vendidas"].to_numpy(dtype=float)
    lluvia = df_sub["precipitacion"].to_numpy(dtype=float)

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=temp_jitter,
            y=unidades,
            mode="markers",
            name="Histórico diario (codificado por lluvia mm)",
            marker=dict(
                size=8,
                color=lluvia,
                colorscale=[
                    [0.0, "#D9C3B0"],
                    [0.5, "#C77C55"],
                    [1.0, "#382820"],
                ],
                showscale=True,
                colorbar=dict(
                    title=dict(text="Lluvia (mm)", font=dict(size=10, color="#81756F")),
                    tickfont=dict(family="JetBrains Mono, monospace", size=9.5, color="#81756F"),
                    thickness=12,
                    len=0.75,
                ),
                opacity=0.78,
                line=dict(color="#FFFFFF", width=0.8),
            ),
            customdata=np.stack([df_sub["fecha"], lluvia], axis=-1),
            hovertemplate=(
                "Fecha: <b>%{customdata[0]}</b><br>"
                "Temp: <b>%{x:.1f} °C</b><br>"
                "Lluvia: <b>%{customdata[1]:.1f} mm</b><br>"
                "Demanda: <b>%{y:,.0f} uds</b><extra></extra>"
            ),
        )
    )

    # Línea de tendencia lineal empírica
    if len(temp_jitter) > 2:
        coef = np.polyfit(temp_jitter, unidades, 1)
        x_line = np.linspace(float(temp_jitter.min()), float(temp_jitter.max()), 30)
        y_line = coef[0] * x_line + coef[1]
        fig.add_trace(
            go.Scatter(
                x=x_line,
                y=y_line,
                mode="lines",
                name="Tendencia térmica lineal",
                line=dict(color="#7B5641", width=2, dash="dash"),
                hoverinfo="skip",
            )
        )

    # Marcador distintivo del escenario simulado actual
    fig.add_trace(
        go.Scatter(
            x=[sim_temp],
            y=[sim_pred],
            mode="markers+text",
            name=f"Escenario simulado ({sim_temp:.1f}°C, {sim_rain:.0f}mm)",
            marker=dict(
                symbol="star",
                size=16,
                color="#BA1A1A",
                line=dict(color="#FFFFFF", width=2),
            ),
            text=[f"  Simulación: {sim_pred:,.0f} uds"],
            textposition="middle right",
            textfont=dict(family="JetBrains Mono, monospace", size=11, color="#BA1A1A"),
            hovertemplate=(
                f"<b>ESCENARIO SIMULADO ACTUAL</b><br>"
                f"Temperatura: {sim_temp:.1f} °C<br>"
                f"Precipitación: {sim_rain:.1f} mm<br>"
                f"Predicción IA: <b>{sim_pred:,.1f} uds</b><extra></extra>"
            ),
        )
    )

    fig = _apply_figma_layout(
        fig,
        height=340,
        xaxis_title="Temperatura Promedio Diaria (°C)",
        yaxis_title="Demanda Diaria (unidades)",
    )
    fig.update_layout(hovermode="closest")
    return fig


def plot_historico_evolucion_semestral(df_daily: pd.DataFrame) -> go.Figure:
    """Vista 4 (Análisis histórico - Gráfica 1): Evolución de ventas diarias Enero - Junio 2023 + Media móvil 7d."""
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=df_daily["fecha"],
            y=df_daily["unidades_vendidas"],
            mode="lines",
            name="Volumen diario",
            fill="tozeroy",
            fillcolor="rgba(56, 40, 32, 0.12)",
            line=dict(color="#382820", width=1.6),
            hovertemplate="Volumen diario: <b>%{y:,.0f} uds</b><extra></extra>",
        )
    )

    fig.add_trace(
        go.Scatter(
            x=df_daily["fecha"],
            y=df_daily["media_7d"],
            mode="lines",
            name="Media móvil (7d)",
            line=dict(color="#C77C55", width=2.6),
            hovertemplate="Media móvil 7d: <b>%{y:,.0f} uds</b><extra></extra>",
        )
    )

    if not df_daily.empty:
        max_row = df_daily.loc[df_daily["unidades_vendidas"].idxmax()]
        fig.add_annotation(
            x=max_row["fecha"],
            y=float(max_row["unidades_vendidas"]),
            text=f"Máx: {max_row['unidades_vendidas']:,.0f} uds ({max_row['fecha']})",
            showarrow=True,
            arrowhead=2,
            arrowcolor="#382820",
            ax=-40,
            ay=-28,
            bgcolor="#382820",
            borderpad=4,
            font=dict(family="JetBrains Mono, monospace", size=10, color="#FFFFFF"),
        )

    return _apply_figma_layout(fig, height=310, yaxis_title="Unidades vendidas / día")


def plot_historico_estacionalidad_semanal(df_dow: pd.DataFrame) -> go.Figure:
    """Vista 4 (Análisis histórico - Gráfica 2): Demanda por día de la semana, apilada por sucursal."""
    fig = go.Figure()
    sucursales = [col for col in df_dow.columns if col not in ("dia_nombre", "total")]
    colores = ["#382820", "#7B5641", "#C77C55"]
    for i, suc in enumerate(sucursales):
        es_ultima = i == len(sucursales) - 1
        fig.add_trace(
            go.Bar(
                y=df_dow["dia_nombre"],
                x=df_dow[suc],
                name=suc,
                orientation="h",
                marker=dict(color=colores[i % len(colores)]),
                text=[f"{t:,.0f}" for t in df_dow["total"]] if es_ultima else None,
                textposition="outside" if es_ultima else None,
                textfont=dict(family="JetBrains Mono, monospace", size=10.5, color="#22140D"),
                hovertemplate=f"{suc}: <b>%{{x:,.0f}} uds</b><extra></extra>",
            )
        )

    fig = _apply_figma_layout(fig, height=300, xaxis_title="Unidades acumuladas en el periodo")
    fig.update_layout(barmode="stack", yaxis=dict(autorange="reversed", showgrid=False))
    max_total = float(df_dow["total"].max()) if len(df_dow) else 0.0
    if max_total > 0:
        fig.update_xaxes(range=[0, max_total * 1.18])  # espacio para la etiqueta del total
    return fig


def plot_historico_curva_intradia(curva: list[dict[str, Any]]) -> go.Figure:
    """Vista 4 (Análisis histórico - Gráfica 5): tickets promedio por hora calculados del dataset Maven filtrado."""
    horas = [c["hora"] for c in curva]
    tickets_hr = [c["tickets"] for c in curva]

    fig = go.Figure()
    if not tickets_hr or max(tickets_hr) <= 0:
        return _apply_figma_layout(fig, height=265, yaxis_title="Tickets / hora", show_legend=False)

    idx_pico = int(max(range(len(tickets_hr)), key=lambda i: tickets_hr[i]))
    x0 = horas[max(0, idx_pico - 1)]
    x1 = horas[min(len(horas) - 1, idx_pico + 1)]
    fig.add_vrect(
        x0=x0,
        x1=x1,
        fillcolor="rgba(199, 124, 85, 0.14)",
        layer="below",
        line_width=0,
    )
    fig.add_trace(
        go.Scatter(
            x=horas,
            y=tickets_hr,
            mode="lines+markers",
            name="Flujo horario promedio (tickets/h)",
            fill="tozeroy",
            fillcolor="rgba(56, 40, 32, 0.08)",
            line=dict(color="#22140D", width=2.5, shape="spline", smoothing=0.6),
            marker=dict(size=6, color="#382820"),
            hovertemplate="Flujo medio: <b>%{y} tickets/h</b><extra></extra>",
        )
    )
    fig.add_annotation(
        x=horas[idx_pico],
        y=tickets_hr[idx_pico],
        text=f"PICO ({tickets_hr[idx_pico]:.0f} tkt/h)",
        showarrow=True,
        arrowhead=2,
        arrowcolor="#7B5641",
        ax=15,
        ay=-25,
        bgcolor="#FAF2EE",
        bordercolor="#EDD4C7",
        borderpad=4,
        font=dict(family="JetBrains Mono, monospace", size=9.5, color="#7B5641"),
    )
    return _apply_figma_layout(fig, height=265, yaxis_title="Tickets / hora", show_legend=False)


def plot_benchmark_modelos(experiments: list[dict[str, Any]]) -> go.Figure:
    """Vista 5 (Estado de datos y modelo): Comparativa de WAPE (%) en Test Set de los 8 experimentos."""
    df_exp = pd.DataFrame(experiments).iloc[::-1]
    colors = ["#72856B" if g else ("#81756F" if "Baseline" in e else "#382820") for g, e in zip(df_exp["es_ganador"], df_exp["experimento"])]

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            y=df_exp["experimento"],
            x=df_exp["wape_test"],
            orientation="h",
            name="WAPE Test (%)",
            marker=dict(color=colors),
            text=[f"{w:.2f}% (MAE {m:.2f})" for w, m in zip(df_exp["wape_test"], df_exp["mae"])],
            textposition="outside",
            textfont=dict(family="JetBrains Mono, monospace", size=10.5, color="#22140D"),
            hovertemplate="<b>%{y}</b><br>WAPE Test: <b>%{x:.2f}%</b><extra></extra>",
        )
    )
    fig = _apply_figma_layout(
        fig,
        height=320,
        xaxis_title="WAPE en Test Set (%) — Menor es mejor",
        show_legend=False,
        margin=dict(l=190, r=90, t=16, b=36),
    )
    fig.update_layout(xaxis=dict(range=[0, 32]), yaxis=dict(showgrid=False))
    return fig


def plot_feature_importance(features: list[dict[str, Any]]) -> go.Figure:
    """Vista 5 (Estado de datos y modelo): Top 10 variables más influyentes del modelo ganador."""
    df_feat = pd.DataFrame(features).iloc[::-1]
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            y=df_feat["feature"],
            x=df_feat["importance"],
            orientation="h",
            marker=dict(color="#7B5641"),
            text=[f"{imp:.1f}%" for imp in df_feat["importance"]],
            textposition="outside",
            textfont=dict(family="JetBrains Mono, monospace", size=10.5, color="#22140D"),
            customdata=df_feat["label"],
            hovertemplate="<b>%{y}</b> (%{customdata})<br>Importancia: <b>%{x:.1f}%</b><extra></extra>",
        )
    )
    fig = _apply_figma_layout(
        fig,
        height=320,
        xaxis_title="Importancia relativa (%)",
        show_legend=False,
        margin=dict(l=140, r=60, t=16, b=36),
    )
    fig.update_layout(xaxis=dict(range=[0, 21]), yaxis=dict(showgrid=False))
    return fig
