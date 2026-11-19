"""Puente desacoplado entre el Frontend (modelo-front) y el Backend de IA (modelo).

Cumple con RNF-03 (Desacoplamiento de Código): la interfaz de usuario consume el modelo
únicamente a través del contrato `predecir(datos_entrada)` de `src/models/predict.py`.
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import streamlit as st

FRONT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BACKEND_ROOT = FRONT_ROOT.parent / "modelo"
BACKEND_ROOT = Path(os.environ.get("CAFESMART_BACKEND_DIR", str(DEFAULT_BACKEND_ROOT))).resolve()

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

# Importación del contrato desacoplado de inferencia del backend (Entrega 3)
from src.config import ALL_MODEL_FEATURES, CUTOFF_DATE, STORE_STATE_MAP  # type: ignore
from src.models.predict import predecir as _backend_predecir  # type: ignore

CORE_CATEGORIES = ["Coffee", "Tea", "Bakery", "Drinking Chocolate"]

STORE_METADATA: dict[str, dict[str, Any]] = {
    "Lower Manhattan": {
        "estado_mx": "Nuevo León",
        "clima_perfil": "Semiárido • Amplia oscilación térmica",
        "zona_ny": "Distrito Financiero (Corporativo Lun-Vie)",
        "cielo_default": "Parcialmente nublado",
    },
    "Hell's Kitchen": {
        "estado_mx": "Ciudad de México",
        "clima_perfil": "Templado de altitud • Lluvia moderada",
        "zona_ny": "Midtown West (Mixto Turístico/Residencial)",
        "cielo_default": "Templado despejado",
    },
    "Astoria": {
        "estado_mx": "Quintana Roo",
        "clima_perfil": "Cálido húmedo • Alta precipitación",
        "zona_ny": "Queens (Residencial • Pico Fin de Semana)",
        "cielo_default": "Húmedo / Nubosidad variable",
    },
}

CATEGORY_COLORS: dict[str, str] = {
    "Coffee": "#382820",
    "Tea": "#7B5641",
    "Bakery": "#C77C55",
    "Drinking Chocolate": "#81756F",
    "Flavours": "#72856B",
    "Coffee beans": "#A3661C",
    "Loose Tea": "#A58E83",
    "Branded": "#6E5A50",
    "Packaged Chocolate": "#B5A89F",
}

CASOS_DEMO: dict[str, dict[str, Any]] = {
    "Personalizado (Controles manuales)": {},
    "Caso 1: Lunes operativo en Lower Manhattan (Escenario Figma)": {
        "store_location": "Lower Manhattan",
        "product_category": "Coffee",
        "fecha": "2023-06-26",
        "temp_min": 19.0,
        "temp_media": 24.0,
        "temp_max": 26.0,
        "precipitacion": 15.0,
        "turno": "Turno Mañana (06:00 - 14:00)",
        "descripcion": "Escenario base del mockup de alta fidelidad: lunes 26 de junio en Lower Manhattan con 24°C.",
    },
    "Caso 2: Lunes lluvioso en Astoria (Demo Entrega 3 - Quintana Roo)": {
        "store_location": "Astoria",
        "product_category": "Coffee",
        "fecha": "2023-07-03",
        "temp_media": 29.5,
        "precipitacion": 82.0,
        "turno": "Turno Mañana (06:00 - 14:00)",
        "descripcion": "Prueba unitaria oficial de Entrega 3: alta precipitación (82 mm) en Astoria -> 239.6 uds estimadas.",
    },
    "Caso 3: Fin de semana soleado en Hell's Kitchen (CDMX)": {
        "store_location": "Hell's Kitchen",
        "product_category": "Bakery",
        "fecha": "2023-06-24",
        "temp_min": 15.0,
        "temp_media": 23.5,
        "temp_max": 28.5,
        "precipitacion": 2.0,
        "turno": "Turno Mañana (06:00 - 14:00)",
        "descripcion": "Escenario RF-05 Entrega 2: sábado soleado con alta rotación de repostería matutina.",
    },
    "Caso 4: Día fresco y lluvioso — Bebidas de Cacao en Astoria": {
        "store_location": "Astoria",
        "product_category": "Drinking Chocolate",
        "fecha": "2023-06-28",
        "temp_min": 14.0,
        "temp_media": 18.0,
        "temp_max": 22.0,
        "precipitacion": 45.0,
        "turno": "Turno Tarde (14:00 - 20:00)",
        "descripcion": "Simulación de sensibilidad climática: descenso térmico con lluvia impulsa bebidas calientes.",
    },
    "Caso 5: Viernes pico corporativo en Lower Manhattan": {
        "store_location": "Lower Manhattan",
        "product_category": "Tea",
        "fecha": "2023-06-30",
        "temp_min": 21.0,
        "temp_media": 27.5,
        "temp_max": 33.0,
        "precipitacion": 5.0,
        "turno": "Turno Mañana (06:00 - 14:00)",
        "descripcion": "Cierre de mes y pico semanal corporativo en distrito financiero.",
    },
}

FEATURE_LABELS: dict[str, str] = {
    "dia_mes": "Día del mes (ciclo mensual)",
    "media_movil_28d": "Media móvil 28 días",
    "media_movil_14d": "Media móvil 14 días",
    "media_movil_7d": "Media móvil 7 días",
    "cos_dia_mes": "Coseno ciclo mensual",
    "sin_dia_mes": "Seno ciclo mensual",
    "ratio_7d_28d": "Razón tendencia 7d / 28d",
    "tendencia_7d_28d": "Momentum 7d vs 28d",
    "unidades_lag_1": "Demanda día anterior (Lag-1)",
    "unidades_lag_2": "Demanda hace 2 días (Lag-2)",
    "unidades_lag_3": "Demanda hace 3 días (Lag-3)",
    "unidades_lag_7": "Demanda misma día sem. pasada (Lag-7)",
    "unidades_lag_14": "Demanda hace 2 semanas (Lag-14)",
    "media_mismo_dow_4s": "Promedio mismo día sem. (4 sem)",
    "std_movil_14d": "Volatilidad móvil 14 días",
    "std_movil_7d": "Volatilidad móvil 7 días",
    "temp_media": "Temperatura media",
    "temp_min": "Temperatura mínima",
    "temp_max": "Temperatura máxima",
    "precipitacion": "Precipitación",
    "amplitud_termica": "Amplitud térmica",
    "dia_semana": "Día de la semana",
    "dias_para_fin_mes": "Días para fin de mes",
}


@st.cache_data(show_spinner=False)
def cargar_resultados_experimentos() -> list[dict[str, Any]]:
    """Lee los 8 experimentos desde `models/experiment_results.json` del backend (fuente única de verdad)."""
    data = json.loads((BACKEND_ROOT / "models" / "experiment_results.json").read_text(encoding="utf-8"))
    ganador = data.get("winner_experiment")
    mejora = data.get("improvement_vs_baseline_pct")
    resultados: list[dict[str, Any]] = []
    for exp in data.get("experiments", []):
        es_ganador = exp["experimento"] == ganador
        test, train = exp.get("test", {}), exp.get("train", {})
        diagnostico = exp.get("diagnostico", "")
        if es_ganador and mejora is not None:
            diagnostico = f"Óptimo • Mejora {mejora:.2f}% vs Baseline ({diagnostico})"
        resultados.append(
            {
                "experimento": exp["experimento"] + (" (GANADOR)" if es_ganador else ""),
                "modelo": exp.get("modelo", ""),
                "hiperparametros": exp.get("hiperparametros", ""),
                "wape_test": float(test.get("wape", 0.0)),
                "wape_train": float(train.get("wape", 0.0)),
                "mae": float(test.get("mae", 0.0)),
                "rmse": float(test.get("rmse", 0.0)),
                "r2": float(test.get("r2", 0.0)),
                "mape_core": float(test.get("mape_core", 0.0)),
                "tiempo_s": float(exp.get("tiempo_train_s", 0.0)),
                "inf_ms": float(exp.get("tiempo_inf_ms", 0.0)),
                "diagnostico": diagnostico,
                "es_ganador": es_ganador,
                "usa_clima": bool(exp.get("usa_clima", True)),
            }
        )
    return resultados


@st.cache_data(show_spinner=False)
def cargar_resumen_experimentos() -> dict[str, Any]:
    """Metadatos globales de la experimentación (mejora vs baseline, delta clima, filas train/test)."""
    data = json.loads((BACKEND_ROOT / "models" / "experiment_results.json").read_text(encoding="utf-8"))
    return {k: v for k, v in data.items() if k != "experiments"}


@st.cache_data(show_spinner=False)
def cargar_importancia_variables(top_n: int = 10) -> list[dict[str, Any]]:
    """Calcula la importancia (split) del modelo ganador serializado, normalizada al 100% del top-N."""
    import joblib

    from src.config import CATEGORICAL_FEATURES, NUMERIC_FEATURES  # type: ignore

    modelo = joblib.load(BACKEND_ROOT / "models" / "modelo_candidato.joblib")
    preproc = joblib.load(BACKEND_ROOT / "models" / "scaler.joblib")
    if not hasattr(modelo, "feature_importances_"):
        return []
    nombres = list(NUMERIC_FEATURES) + list(
        preproc.named_transformers_["cat"].get_feature_names_out(CATEGORICAL_FEATURES)
    )
    imp = np.asarray(modelo.feature_importances_, dtype=float)
    idx = np.argsort(imp)[::-1][:top_n]
    total = float(imp[idx].sum()) or 1.0
    return [
        {
            "feature": nombres[i],
            "label": FEATURE_LABELS.get(nombres[i], nombres[i]),
            "importance": round(float(imp[i]) / total * 100.0, 1),
        }
        for i in idx
    ]


def metricas_ganador() -> dict[str, float]:
    """Métricas de test del modelo ganador según `feature_defaults.json`."""
    return {k: float(v) for k, v in load_feature_defaults()["metricas_test_ganador"].items() if isinstance(v, (int, float))}


@st.cache_data(show_spinner=False)
def load_feature_defaults() -> dict[str, Any]:
    """Carga el archivo feature_defaults.json desde el backend."""
    defaults_path = BACKEND_ROOT / "models" / "feature_defaults.json"
    return json.loads(defaults_path.read_text(encoding="utf-8"))


@st.cache_data(show_spinner=False)
def load_clean_dataset() -> pd.DataFrame:
    """Carga el dataset limpio preprocesado (4,509 registros diarios sin fuga temporal)."""
    csv_path = BACKEND_ROOT / "data" / "processed" / "dataset_limpio.csv"
    df = pd.read_csv(csv_path)
    df["fecha_dt"] = pd.to_datetime(df["fecha"])
    return df


def get_weather_default_for_store(store_location: str, month: int = 6) -> dict[str, float]:
    """Obtiene los valores climáticos de referencia para la sucursal y mes dados."""
    defaults = load_feature_defaults()
    estado = STORE_STATE_MAP.get(store_location, "Nuevo León")
    key = f"{estado}||{month}"
    return defaults.get("weather_defaults", {}).get(
        key,
        {"temp_min": 19.0, "temp_media": 24.0, "temp_max": 28.0, "precipitacion": 15.0},
    )


def get_series_default(store_location: str, product_category: str) -> dict[str, Any]:
    """Obtiene las estadísticas históricas (lags y medias móviles) por sucursal y categoría."""
    defaults = load_feature_defaults()
    key = f"{store_location}||{product_category}"
    return defaults.get("series_defaults", {}).get(key, {})


def ejecutar_inferencia(datos_entrada: dict[str, Any]) -> dict[str, Any]:
    """Ejecuta la función desacoplada `predecir(datos_entrada)` del backend midiendo latencia (RNF-01, RNF-03).

    Soporta tanto la clave `fecha` (Entrega 3) como `fecha_objetivo` (Entrega 2),
    y tanto `temp_media`/`precipitacion` como `avg_temp_c`/`rain_mm`.
    """
    payload = dict(datos_entrada)
    if "fecha" not in payload and "fecha_objetivo" in payload:
        payload["fecha"] = payload["fecha_objetivo"]
    if "temp_media" not in payload and "avg_temp_c" in payload:
        payload["temp_media"] = payload["avg_temp_c"]
    if "precipitacion" not in payload and "rain_mm" in payload:
        payload["precipitacion"] = payload["rain_mm"]

    # Validación explícita de rango (RNF-02)
    temp_media = float(payload.get("temp_media", 24.0))
    precipitacion = float(payload.get("precipitacion", 15.0))
    if temp_media < -10.0 or temp_media > 45.0:
        raise ValueError(
            f"Temperatura media fuera de rango operativo ({temp_media} °C). Ingrese un valor entre -10 °C y 45 °C."
        )
    if precipitacion < 0.0 or precipitacion > 300.0:
        raise ValueError(
            f"Precipitación inválida ({precipitacion} mm). Ingrese un valor entre 0 mm y 300 mm."
        )

    # Respetar los defaults de temp_min y temp_max de predict.py salvo que se envíen explícitamente
    fecha_ts = pd.to_datetime(str(payload.get("fecha", "2023-06-26")))
    store = payload.get("store_location", "Lower Manhattan")
    w_ref = get_weather_default_for_store(store, int(fecha_ts.month))
    temp_min = float(payload["temp_min"]) if "temp_min" in payload else float(w_ref.get("temp_min", 18.0))
    temp_max = float(payload["temp_max"]) if "temp_max" in payload else float(w_ref.get("temp_max", 29.0))
    if "temp_min" in payload and "temp_max" in payload and temp_max < temp_min:
        raise ValueError("Variables meteorológicas inválidas (temp_max < temp_min).")
    payload["temp_media"] = temp_media
    payload["precipitacion"] = precipitacion

    # Si la fecha está dentro del dataset histórico, podemos hidratar los lags reales de esa fecha para máxima fidelidad
    df = load_clean_dataset()
    store = payload.get("store_location", "Lower Manhattan")
    cat = payload.get("product_category", "Coffee")
    fecha_str = str(payload.get("fecha", "2023-06-26"))

    match = df[
        (df["store_location"] == store)
        & (df["product_category"] == cat)
        & (df["fecha"] == fecha_str)
    ]
    unidades_reales_observadas: float | None = None
    if not match.empty:
        row_hist = match.iloc[0]
        unidades_reales_observadas = float(row_hist["unidades_vendidas"])
        for lag_col in [
            "unidades_lag_1",
            "unidades_lag_2",
            "unidades_lag_3",
            "unidades_lag_7",
            "unidades_lag_14",
            "media_movil_7d",
            "media_movil_14d",
            "media_movil_28d",
            "std_movil_7d",
            "std_movil_14d",
            "media_mismo_dow_4s",
        ]:
            if lag_col not in datos_entrada and lag_col in row_hist:
                payload[lag_col] = float(row_hist[lag_col])

    t0 = time.perf_counter()
    resultado = _backend_predecir(payload)
    tiempo_ms = round((time.perf_counter() - t0) * 1000.0, 2)

    defaults = load_feature_defaults()
    series_ref = get_series_default(store, cat)
    fecha_ts = pd.to_datetime(fecha_str)
    dow_str = str(int(fecha_ts.day_of_week))
    media_28d = float(payload.get("media_movil_28d", series_ref.get("media_movil_28d", resultado["unidades_estimadas"])))
    ref_dow = float(
        payload.get(
            "media_mismo_dow_4s",
            series_ref.get("dow_defaults", {}).get(dow_str, media_28d),
        )
    )
    if ref_dow <= 0:
        ref_dow = max(1.0, media_28d)

    pred_uds = float(resultado["unidades_estimadas"])
    delta_pct = round(((pred_uds - ref_dow) / ref_dow) * 100.0, 1) if ref_dow > 0 else 0.0
    mape_core = float(defaults["metricas_test_ganador"]["mape_core"]) / 100.0
    wape_test = float(defaults["metricas_test_ganador"]["wape"])

    # Enriquecer con ambos contratos (Entrega 2 + Entrega 3)
    resultado.update(
        {
            "prediccion_unidades": pred_uds,
            "intervalo_min": float(resultado["rango_estimado_85"][0]),
            "intervalo_max": float(resultado["rango_estimado_85"][1]),
            "clase_etiqueta": resultado["nivel_demanda"],
            "error_mape_referencia": round(mape_core, 4),
            "error_wape_test": wape_test,
            "tiempo_ms": tiempo_ms,
            "ref_historica_dow": round(ref_dow, 1),
            "media_movil_28d": round(media_28d, 1),
            "delta_pct_vs_ref": delta_pct,
            "unidades_reales": unidades_reales_observadas,
            "temp_media": temp_media,
            "temp_min": temp_min,
            "temp_max": temp_max,
            "precipitacion": precipitacion,
        }
    )
    return resultado


def predecir_desglose_tienda(
    store_location: str,
    fecha_str: str,
    temp_media: float,
    precipitacion: float,
    temp_min: float | None = None,
    temp_max: float | None = None,
     solo_core: bool = False,
) -> dict[str, Any]:
    """Ejecuta `predecir()` en todas las categorías de la sucursal para la fecha dada."""
    defaults = load_feature_defaults()
    categorias = CORE_CATEGORIES if solo_core else defaults["categorias_validas"]

    t0 = time.perf_counter()
    desglose: list[dict[str, Any]] = []
    total_estimado = 0.0
    total_recomendado = 0
    total_ref = 0.0
    total_min = 0
    total_max = 0

    for cat in categorias:
        res = ejecutar_inferencia(
            {
                "store_location": store_location,
                "product_category": cat,
                "fecha": fecha_str,
                "temp_media": temp_media,
                "precipitacion": precipitacion,
                **({"temp_min": temp_min} if temp_min is not None else {}),
                **({"temp_max": temp_max} if temp_max is not None else {}),
            }
        )
        desglose.append(res)
        total_estimado += res["unidades_estimadas"]
        total_recomendado += res["unidades_recomendadas"]
        total_ref += res["ref_historica_dow"]
        total_min += res["rango_estimado_85"][0]
        total_max += res["rango_estimado_85"][1]

    tiempo_total_ms = round((time.perf_counter() - t0) * 1000.0, 2)
    desglose_sorted = sorted(desglose, key=lambda x: x["unidades_estimadas"], reverse=True)
    lider = desglose_sorted[0] if desglose_sorted else None
    lider_share = (
        round((lider["unidades_estimadas"] / total_estimado) * 100.0, 1)
        if lider and total_estimado > 0
        else 0.0
    )
    delta_total_pct = (
        round(((total_estimado - total_ref) / total_ref) * 100.0, 1)
        if total_ref > 0
        else 0.0
    )

    if total_estimado >= total_ref * 1.08:
        nivel_global = "Demanda Alta"
    elif total_estimado <= total_ref * 0.90:
        nivel_global = "Demanda Baja"
    else:
        nivel_global = "Demanda Habitual"

    return {
        "sucursal": store_location,
        "estado_clima": STORE_STATE_MAP.get(store_location, "Nuevo León"),
        "fecha": fecha_str,
        "total_unidades_estimadas": round(total_estimado, 1),
        "total_unidades_recomendadas": total_recomendado,
        "total_ref_historica": round(total_ref, 1),
        "delta_total_pct": delta_total_pct,
        "rango_total_85": [total_min, total_max],
        "nivel_demanda_global": nivel_global,
        "categoria_lider": lider["categoria"] if lider else "Coffee",
        "categoria_lider_unidades": lider["unidades_estimadas"] if lider else 0.0,
        "categoria_lider_share": lider_share,
        "desglose": desglose_sorted,
        "tiempo_total_ms": tiempo_total_ms,
    }


def predecir_serie_temporal(
    store_location: str,
    product_category: str,
    fecha_corte_str: str,
    temp_media: float,
    precipitacion: float,
    dias_hist: int = 14,
    dias_futuro: int = 7,
) -> pd.DataFrame:
    """Construye una serie temporal continua: `dias_hist` observados + `dias_futuro` pronosticados con `predecir()`."""
    df = load_clean_dataset()
    defaults = load_feature_defaults()
    todas = product_category == "Todas las categorías"

    fecha_corte = pd.to_datetime(fecha_corte_str)
    max_dataset_date = df["fecha_dt"].max()
    min_dataset_date = df["fecha_dt"].min()

    # Si la fecha elegida es posterior al fin del dataset (2023-06-30), anclamos la historia en los últimos días de junio
    anchor_hist_end = min(fecha_corte - timedelta(days=1), max_dataset_date)
    anchor_hist_start = max(anchor_hist_end - timedelta(days=dias_hist - 1), min_dataset_date)

    df_store = df[df["store_location"] == store_location]
    if not todas:
        df_store = df_store[df_store["product_category"] == product_category]

    df_hist_window = (
        df_store[(df_store["fecha_dt"] >= anchor_hist_start) & (df_store["fecha_dt"] <= anchor_hist_end)]
        .groupby("fecha", as_index=False)
        .agg(
            unidades_reales=("unidades_vendidas", "sum"),
            media_7d=("media_movil_7d", "sum"),
        )
        .sort_values("fecha")
    )

    registros: list[dict[str, Any]] = []
    for _, r in df_hist_window.iterrows():
        f_dt = pd.to_datetime(r["fecha"])
        dias_esp = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
        etiqueta = f"{dias_esp[f_dt.day_of_week]} {f_dt.day:02d}"
        registros.append(
            {
                "fecha": r["fecha"],
                "etiqueta": etiqueta,
                "tipo": "Histórico real",
                "unidades_reales": round(float(r["unidades_reales"]), 1),
                "pronostico": None,
                "intervalo_min": None,
                "intervalo_max": None,
                "media_ref": round(float(r["media_7d"]), 1),
            }
        )

    # Pronóstico de `dias_futuro` días hacia adelante a partir de fecha_corte
    categorias_eval = defaults["categorias_validas"] if todas else [product_category]
    for d in range(dias_futuro):
        f_proj = fecha_corte + timedelta(days=d)
        f_str = f_proj.strftime("%Y-%m-%d")
        dias_esp = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
        etiqueta = f"{dias_esp[f_proj.day_of_week]} {f_proj.day:02d}*"

        suma_pred = 0.0
        suma_min = 0.0
        suma_max = 0.0
        suma_ref = 0.0
        for cat in categorias_eval:
            res = ejecutar_inferencia(
                {
                    "store_location": store_location,
                    "product_category": cat,
                    "fecha": f_str,
                    "temp_media": temp_media,
                    "precipitacion": precipitacion,
                }
            )
            suma_pred += res["unidades_estimadas"]
            suma_min += res["rango_estimado_85"][0]
            suma_max += res["rango_estimado_85"][1]
            suma_ref += res["ref_historica_dow"]

        # Verificar si también existe observación real en el dataset (backtesting en Junio 2023)
        real_obs = None
        df_real_day = df_store[df_store["fecha"] == f_str]
        if not df_real_day.empty:
            real_obs = round(float(df_real_day["unidades_vendidas"].sum()), 1)

        registros.append(
            {
                "fecha": f_str,
                "etiqueta": etiqueta,
                "tipo": "Pronóstico",
                "unidades_reales": real_obs,
                "pronostico": round(suma_pred, 1),
                "intervalo_min": round(suma_min, 1),
                "intervalo_max": round(suma_max, 1),
                "media_ref": round(suma_ref, 1),
            }
        )

    return pd.DataFrame(registros)


HORAS_OPERACION = list(range(6, 21))  # 06:00 a 20:00 (rango real del dataset Maven)
HORA_CAMBIO_TURNO = 14  # Turno Mañana 06:00-14:00 / Turno Tarde 14:00-20:00
TODAS_SUCURSALES = ("Todas las sucursales", "Todas las sucursales (3)")


@st.cache_data(show_spinner=False)
def load_transacciones() -> pd.DataFrame:
    """Carga las transacciones crudas de Maven (con hora y precio) para análisis intradía e histórico."""
    csv_path = BACKEND_ROOT / "data" / "raw" / "Coffee Shop Sales.csv"
    df = pd.read_csv(csv_path)
    df["fecha_dt"] = pd.to_datetime(df["transaction_date"], format="%m/%d/%y")
    df["hora"] = pd.to_datetime(df["transaction_time"], format="%H:%M:%S").dt.hour
    df["dia_semana"] = df["fecha_dt"].dt.dayofweek
    df["importe"] = df["transaction_qty"] * df["unit_price"]
    return df


def _filtrar_transacciones(
    store_location: str | None = None,
    product_category: str | None = None,
    dia_semana: int | None = None,
) -> pd.DataFrame:
    df = load_transacciones()
    if store_location and store_location not in TODAS_SUCURSALES:
        df = df[df["store_location"] == store_location]
    if product_category and product_category != "Todas las categorías":
        df = df[df["product_category"] == product_category]
    if dia_semana is not None:
        df = df[df["dia_semana"] == dia_semana]
    return df


@st.cache_data(show_spinner=False)
def perfil_horario_real(
    store_location: str | None = None,
    product_category: str | None = None,
    dia_semana: int | None = None,
) -> pd.DataFrame:
    """Perfil intradía observado: unidades promedio por hora y participación del día.

    Si el filtro por día de la semana deja muy pocas observaciones, se usa el perfil de todos los días.
    """
    df = _filtrar_transacciones(store_location, product_category, dia_semana)
    if dia_semana is not None and df["transaction_qty"].sum() < 200:
        df = _filtrar_transacciones(store_location, product_category, None)
    n_dias = max(1, df["fecha_dt"].nunique())
    por_hora = df.groupby("hora")["transaction_qty"].sum().reindex(HORAS_OPERACION, fill_value=0)
    tickets = df.groupby("hora").size().reindex(HORAS_OPERACION, fill_value=0)
    total = float(por_hora.sum()) or 1.0
    return pd.DataFrame(
        {
            "hora_int": HORAS_OPERACION,
            "hora": [f"{h:02d}:00" for h in HORAS_OPERACION],
            "uds_promedio": (por_hora.values / n_dias).round(1),
            "tickets_promedio": (tickets.values / n_dias).round(1),
            "share": por_hora.values / total,
        }
    )


def generar_curva_horaria(
    unidades_dia_pred: float,
    unidades_dia_ref: float,
    store_location: str = "Lower Manhattan",
    product_category: str = "Todas las categorías",
    fecha_str: str | None = None,
    rango_dia_85: tuple[float, float] | list[float] | None = None,
) -> pd.DataFrame:
    """Distribuye la predicción diaria del modelo en 06:00-20:00 con el perfil horario REAL de Maven.

    - `historico_observado`: promedio real de unidades por hora (misma sucursal/categoría/día de la semana).
    - `pronostico_proyectado`: predicción diaria de `predecir()` × participación horaria observada.
    - `rango_min`/`rango_max`: banda al 85% de `predecir()` repartida con la misma participación.
    """
    dow = int(pd.to_datetime(fecha_str).day_of_week) if fecha_str else None
    perfil = perfil_horario_real(store_location, product_category, dow)
    if rango_dia_85 is None:
        wape = metricas_ganador().get("wape", 15.0) / 100.0
        rango_dia_85 = (unidades_dia_pred * (1 - wape), unidades_dia_pred * (1 + wape))
    r_min, r_max = float(rango_dia_85[0]), float(rango_dia_85[1])

    rows = []
    for _, r in perfil.iterrows():
        share = float(r["share"])
        rows.append(
            {
                "hora": r["hora"],
                "turno": "Turno Mañana" if int(r["hora_int"]) < HORA_CAMBIO_TURNO else "Turno Tarde",
                "historico_observado": float(r["uds_promedio"]),
                "pronostico_proyectado": round(unidades_dia_pred * share, 1),
                "rango_min": round(max(0.0, r_min * share), 1),
                "rango_max": round(r_max * share, 1),
            }
        )
    return pd.DataFrame(rows)


def describir_curva_horaria(df_horaria: pd.DataFrame) -> dict[str, str]:
    """Hora pico y valle (entre el pico y las 17:00) de una curva horaria."""
    idx_pico = int(df_horaria["pronostico_proyectado"].idxmax())
    pico = df_horaria.loc[idx_pico]
    tramo = df_horaria.iloc[idx_pico + 1 : len(df_horaria) - 3]
    valle = tramo.loc[tramo["pronostico_proyectado"].idxmin()] if not tramo.empty else pico
    return {
        "hora_pico": str(pico["hora"]),
        "uds_pico": f"{float(pico['pronostico_proyectado']):.0f}",
        "hora_valle": str(valle["hora"]),
        "uds_valle": f"{float(valle['pronostico_proyectado']):.0f}",
    }


def _share_franja(perfil: pd.DataFrame, inicio: int, fin: int) -> float:
    horas = perfil["hora_int"]
    mask = (horas >= inicio) & ((horas < fin) | ((fin == 20) & (horas == 20)))
    return float(perfil.loc[mask, "share"].sum())


def generar_tabla_franjas_detalle(
    store_location: str,
    fecha_str: str,
    desglose_categorias: list[dict[str, Any]],
) -> pd.DataFrame:
    """Tabla por franja horaria y categoría: predicción diaria × participación REAL de la franja.

    La referencia histórica usa el promedio del mismo día de la semana (`ref_historica_dow`)
    repartido con la misma participación observada.
    """
    f_dt = pd.to_datetime(fecha_str)
    dow = int(f_dt.day_of_week)
    meses_esp = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
    fecha_corta = f"{f_dt.day:02d} {meses_esp[f_dt.month - 1]}"
    franjas = [(7, 9), (9, 11), (11, 14), (14, 17), (17, 20)]

    filas = []
    core = [d for d in desglose_categorias if d["categoria"] in CORE_CATEGORIES] or desglose_categorias
    for info in sorted(core, key=lambda x: x["unidades_estimadas"], reverse=True):
        cat = info["categoria"]
        perfil = perfil_horario_real(store_location, cat, dow)
        for inicio, fin in franjas:
            share_franja = _share_franja(perfil, inicio, fin)
            est_franja = int(round(info["unidades_estimadas"] * share_franja))
            ref_franja = int(round(info["ref_historica_dow"] * share_franja))
            if est_franja < 1 or ref_franja < 1:
                continue
            var_pct = round(((est_franja - ref_franja) / ref_franja) * 100.0, 1)
            if var_pct >= 10.0:
                estado, nivel = f"Demanda alta respecto al historial ({var_pct:+.0f}%)", "Alta"
            elif var_pct <= -8.0:
                estado, nivel = f"Demanda ligeramente baja ({var_pct:+.0f}%)", "Baja"
            else:
                estado, nivel = f"Demanda similar al patrón habitual ({var_pct:+.0f}%)", "Habitual"
            filas.append(
                {
                    "fecha_franja": f"{fecha_corta} ({inicio:02d}:00 - {fin:02d}:00)",
                    "sucursal": store_location,
                    "categoria": cat,
                    "unidades_estimadas": est_franja,
                    "ref_historica": ref_franja,
                    "variacion_pct": var_pct,
                    "estado_explicativo": estado,
                    "nivel": nivel,
                }
            )
    return pd.DataFrame(filas)


def items_revision_stock(desglose_categorias: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Categorías que `predecir()` etiqueta como "Demanda Alta" para la sucursal y fecha (ordenadas por delta)."""
    alertas = [d for d in desglose_categorias if d.get("nivel_demanda") == "Demanda Alta"]
    return sorted(alertas, key=lambda d: float(d.get("delta_pct_vs_ref", 0.0)), reverse=True)


@st.cache_data(show_spinner=False)
def resumen_historico(
    store_location: str | None,
    product_category: str | None,
    fecha_ini: str,
    fecha_fin: str,
    hora_ini: int = 6,
    hora_fin: int = 20,
) -> dict[str, Any]:
    """Agrega las transacciones reales de Maven según los filtros de la vista Análisis histórico."""
    df = _filtrar_transacciones(None, product_category, None)
    df = df[(df["fecha_dt"] >= pd.to_datetime(fecha_ini)) & (df["fecha_dt"] <= pd.to_datetime(fecha_fin))]
    df = df[(df["hora"] >= hora_ini) & (df["hora"] <= hora_fin)]
    df_red = df  # las 3 sucursales, para la comparativa territorial
    if store_location and store_location not in TODAS_SUCURSALES:
        df = df[df["store_location"] == store_location]

    unidades = int(df["transaction_qty"].sum())
    tickets = int(len(df))
    dias = max(1, df["fecha_dt"].nunique())
    diario = df.groupby("fecha_dt").agg(q=("transaction_qty", "sum"), t=("transaction_id", "size"))
    ratio_diario = diario["q"] / diario["t"] if not diario.empty else pd.Series([0.0])

    por_tienda = (
        df_red.groupby("store_location")
        .agg(unidades=("transaction_qty", "sum"), tickets=("transaction_id", "size"))
        .sort_values("unidades", ascending=False)
    )
    total_red = float(por_tienda["unidades"].sum()) or 1.0
    tiendas = [
        {
            "sucursal": idx,
            "estado_mx": STORE_STATE_MAP.get(idx, ""),
            "unidades": int(r["unidades"]),
            "tickets": int(r["tickets"]),
            "share": round(float(r["unidades"]) / total_red * 100.0, 1),
            "uds_ticket": round(float(r["unidades"]) / max(1, int(r["tickets"])), 2),
        }
        for idx, r in por_tienda.iterrows()
    ]

    por_cat = (
        df.groupby("product_category")
        .agg(tickets=("transaction_id", "size"), unidades=("transaction_qty", "sum"), importe=("importe", "sum"))
        .sort_values("unidades", ascending=False)
    )
    total_uds = float(unidades) or 1.0
    categorias = []
    for cat, r in por_cat.iterrows():
        lider_s = df_red[df_red["product_category"] == cat].groupby("store_location")["transaction_qty"].sum()
        h = df[df["product_category"] == cat].groupby("hora")["transaction_qty"].sum()
        categorias.append(
            {
                "categoria": cat,
                "tickets": int(r["tickets"]),
                "unidades": int(r["unidades"]),
                "share": round(float(r["unidades"]) / total_uds * 100.0, 1),
                "precio_prom": round(float(r["importe"]) / max(1.0, float(r["unidades"])), 2),
                "sucursal_lider": lider_s.idxmax() if not lider_s.empty else "-",
                "sucursal_lider_pct": round(float(lider_s.max()) / max(1.0, float(lider_s.sum())) * 100.0, 1)
                if not lider_s.empty
                else 0.0,
                "hora_pico": f"{int(h.idxmax()):02d}:00" if not h.empty else "-",
            }
        )

    por_hora = df.groupby("hora").size().reindex(range(hora_ini, hora_fin + 1), fill_value=0) / dias
    return {
        "unidades": unidades,
        "tickets": tickets,
        "dias": dias,
        "tickets_dia": int(round(tickets / dias)),
        "uds_ticket": round(unidades / max(1, tickets), 2),
        "uds_ticket_std": round(float(ratio_diario.std(ddof=0)), 2) if len(ratio_diario) > 1 else 0.0,
        "importe": round(float(df["importe"].sum()), 2),
        "precio_prom": round(float(df["importe"].sum()) / max(1, unidades), 2),
        "tiendas": tiendas,
        "categorias": categorias,
        "curva_tickets_hora": [{"hora": f"{h:02d}h", "tickets": round(float(v), 1)} for h, v in por_hora.items()],
    }


def generar_recomendaciones_turno(
    store_location: str,
    fecha_str: str,
    desglose_categorias: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Genera las 6 recomendaciones operativas de inventario vinculadas con las predicciones reales."""
    cat_map = {item["categoria"]: item for item in desglose_categorias}

    coffee_pred = cat_map.get("Coffee", {}).get("unidades_estimadas", 240.0)
    bakery_pred = cat_map.get("Bakery", {}).get("unidades_estimadas", 65.0)
    tea_pred = cat_map.get("Tea", {}).get("unidades_estimadas", 180.0)
    choco_pred = cat_map.get("Drinking Chocolate", {}).get("unidades_estimadas", 45.0)

    # Escalar de forma realista según las predicciones del modelo para la tienda y fecha
    brewed_tazas = int(round(coffee_pred * 1.15))
    brewed_sug = int(round(brewed_tazas * 1.072))

    espresso_kg = round(coffee_pred * 0.055, 1)
    espresso_sug = round(espresso_kg * 1.08, 1)

    croissant_uds = int(round(bakery_pred * 1.10))
    croissant_sug = int(round(croissant_uds * 1.085))

    earl_grey_inf = int(round(tea_pred * 0.38))
    earl_grey_sug = int(round(earl_grey_inf * 1.075))

    choco_tazas = int(round(choco_pred * 1.0))
    choco_sug = int(round(choco_tazas * 1.10))

    bagel_uds = int(round(bakery_pred * 0.78))
    bagel_sug = int(round(bagel_uds * 1.11))

    return [
        {
            "id": "rec_1",
            "producto": "Brewed Coffee - Dark Roast",
            "subtitulo": "LOTE GRANDE • FILTRO BATCH",
            "categoria": "Coffee",
            "sucursal": store_location,
            "demanda_estimada": f"{brewed_tazas} tazas",
            "demanda_num": brewed_tazas,
            "margen_seguridad": "+7.2% (WAPE ref.)",
            "cant_sugerida": f"~{brewed_sug} tazas",
            "motivo": "Pico habitual matutino 07:30 - 09:30",
            "prioridad": "Revisado",
            "estado_default": "Revisado por encargado",
            "checked_default": True,
        },
        {
            "id": "rec_2",
            "producto": "Barista Espresso Blend",
            "subtitulo": "GRANOS KG • TOLVA PRINCIPAL",
            "categoria": "Coffee",
            "sucursal": store_location,
            "demanda_estimada": f"{espresso_kg} kg",
            "demanda_num": espresso_kg,
            "margen_seguridad": "+8.0% (Tueste medio)",
            "cant_sugerida": f"~{espresso_sug} kg",
            "motivo": "Alta rotación de bebidas con leche",
            "prioridad": "Pendiente de revisión",
            "estado_default": "Pendiente de revisión",
            "checked_default": False,
        },
        {
            "id": "rec_3",
            "producto": "Croissant de Mantequilla",
            "subtitulo": "BOLLERÍA FRESCA HORNEADA",
            "categoria": "Bakery",
            "sucursal": store_location,
            "demanda_estimada": f"{croissant_uds} uds",
            "demanda_num": croissant_uds,
            "margen_seguridad": "+8.5% (2 tandas)",
            "cant_sugerida": f"~{croissant_sug} uds",
            "motivo": "Demanda concentrada antes de las 10:30",
            "prioridad": "Atención requerida",
            "estado_default": "Atención requerida",
            "checked_default": False,
        },
        {
            "id": "rec_4",
            "producto": "Earl Grey Tea (Porciones)",
            "subtitulo": "TÉ EN HOJA / SACHETS",
            "categoria": "Tea",
            "sucursal": store_location,
            "demanda_estimada": f"{earl_grey_inf} infusiones",
            "demanda_num": earl_grey_inf,
            "margen_seguridad": "+7.5% (Estándar)",
            "cant_sugerida": f"~{earl_grey_sug} infusiones",
            "motivo": "Consumo regular vespertino",
            "prioridad": "Revisado",
            "estado_default": "Revisado",
            "checked_default": True,
        },
        {
            "id": "rec_5",
            "producto": "Hot Chocolate Supreme",
            "subtitulo": "BEBIDA CACAO ARTESANAL",
            "categoria": "Drinking Chocolate",
            "sucursal": store_location,
            "demanda_estimada": f"{choco_tazas} tazas",
            "demanda_num": choco_tazas,
            "margen_seguridad": "+10.0% (Sens. clima)",
            "cant_sugerida": f"~{choco_sug} tazas",
            "motivo": "Demanda estable sensible a lluvia/frío",
            "prioridad": "Revisado",
            "estado_default": "Revisado",
            "checked_default": True,
        },
        {
            "id": "rec_6",
            "producto": "Bagel Clásico con Queso",
            "subtitulo": "PANADERÍA FRESCA • DESAYUNO",
            "categoria": "Bakery",
            "sucursal": store_location,
            "demanda_estimada": f"{bagel_uds} uds",
            "demanda_num": bagel_uds,
            "margen_seguridad": "+11.0% (Cross-sale)",
            "cant_sugerida": f"~{bagel_sug} uds",
            "motivo": "Complemento matutino de alta demanda",
            "prioridad": "Revisado",
            "estado_default": "Revisado por encargado",
            "checked_default": True,
        },
    ]
