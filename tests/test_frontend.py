"""Pruebas funcionales automatizadas del Frontend CaféSmart AI (RF-01 a RF-05 y RNF-01 a RNF-03)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.backend_bridge import (
    CASOS_DEMO,
    cargar_importancia_variables,
    cargar_resultados_experimentos,
    ejecutar_inferencia,
    generar_curva_horaria,
    generar_recomendaciones_turno,
    generar_tabla_franjas_detalle,
    items_revision_stock,
    load_transacciones,
    perfil_horario_real,
    predecir_desglose_tienda,
    resumen_historico,
)


def test_contrato_desacoplado_y_latencia_rnf01_rnf03() -> None:
    """Verifica que el puente consuma predecir() de forma desacoplada en menos de 500 ms (RNF-01)."""
    res = ejecutar_inferencia(
        {
            "store_location": "Astoria",
            "product_category": "Coffee",
            "fecha": "2023-07-03",
            "temp_media": 29.5,
            "precipitacion": 82.0,
        }
    )
    assert res["status"] == "success"
    assert res["unidades_estimadas"] == 239.6
    assert res["unidades_recomendadas"] == 240
    assert res["rango_estimado_85"] == [215, 264]
    assert res["tiempo_ms"] < 500.0
    # Compatibilidad con contrato Entrega 2
    assert "prediccion_unidades" in res
    assert "intervalo_min" in res
    assert "intervalo_max" in res
    assert "clase_etiqueta" in res
    assert "error_mape_referencia" in res


def test_manejo_entradas_invalidas_rnf02() -> None:
    """Verifica que entradas fuera de rango lancen ValueError controlado para st.error/st.warning."""
    for bad_payload in [
        {"store_location": "Sucursal Inexistente", "product_category": "Coffee", "fecha": "2023-06-26"},
        {"store_location": "Astoria", "product_category": "Coffee", "fecha": "2023-06-26", "temp_media": 85.0},
    ]:
        raised = False
        try:
            ejecutar_inferencia(bad_payload)
        except ValueError:
            raised = True
        assert raised, f"Se esperaba ValueError para {bad_payload}"


def test_casos_demo_rf05() -> None:
    """Verifica que todos los casos de demostración precargados ejecuten inferencia válida."""
    for nombre, payload in CASOS_DEMO.items():
        if not payload:
            continue
        res = ejecutar_inferencia(payload)
        assert res["unidades_estimadas"] >= 0
        assert res["status"] == "success"


def test_desglose_y_tablas_operativas() -> None:
    """Verifica la generación de desglose por tienda, curva horaria y guía de inventario."""
    resumen = predecir_desglose_tienda("Lower Manhattan", "2023-06-26", 24.0, 15.0)
    assert resumen["total_unidades_estimadas"] > 0
    assert len(resumen["desglose"]) == 9

    df_horaria = generar_curva_horaria(
        resumen["total_unidades_estimadas"],
        resumen["total_ref_historica"],
        "Lower Manhattan",
    )
    assert len(df_horaria) == 15

    df_franjas = generar_tabla_franjas_detalle("Lower Manhattan", "2023-06-26", resumen["desglose"])
    assert not df_franjas.empty

    recs = generar_recomendaciones_turno("Lower Manhattan", "2023-06-26", resumen["desglose"])
    assert len(recs) == 6


def test_curva_horaria_usa_perfil_real_y_rango_del_modelo() -> None:
    """La curva reparte la predicción diaria (suma conservada) y la banda 85% de predecir()."""
    res = ejecutar_inferencia(
        {"store_location": "Astoria", "product_category": "Coffee", "fecha": "2023-06-26", "temp_media": 24.0, "precipitacion": 15.0}
    )
    df = generar_curva_horaria(
        res["unidades_estimadas"], res["ref_historica_dow"], "Astoria", "Coffee", "2023-06-26", res["rango_estimado_85"]
    )
    assert abs(df["pronostico_proyectado"].sum() - res["unidades_estimadas"]) < 1.0
    assert abs(df["rango_max"].sum() - res["rango_estimado_85"][1]) < 1.0
    assert (df["rango_min"] <= df["pronostico_proyectado"]).all()
    assert (df["pronostico_proyectado"] <= df["rango_max"]).all()
    # El histórico observado proviene de las transacciones reales, no de pesos fijos
    perfil = perfil_horario_real("Astoria", "Coffee", 0)
    assert df["historico_observado"].tolist() == perfil["uds_promedio"].tolist()


def test_resumen_historico_coincide_con_csv() -> None:
    """Los totales del Análisis histórico se calculan del CSV real de Maven."""
    tx = load_transacciones()
    r = resumen_historico(None, None, "2023-01-01", "2023-06-30")
    assert r["unidades"] == int(tx["transaction_qty"].sum())
    assert r["tickets"] == len(tx)
    assert abs(sum(t["share"] for t in r["tiendas"]) - 100.0) < 0.5
    r_ast = resumen_historico("Astoria", "Bakery", "2023-06-01", "2023-06-30", 6, 13)
    esperado = tx[
        (tx["store_location"] == "Astoria")
        & (tx["product_category"] == "Bakery")
        & (tx["fecha_dt"] >= "2023-06-01")
        & (tx["hora"] <= 13)
    ]["transaction_qty"].sum()
    assert r_ast["unidades"] == int(esperado)


def test_experimentos_e_importancias_desde_artefactos() -> None:
    """Los resultados de los experimentos y la importancia salen de los artefactos del backend."""
    exps = cargar_resultados_experimentos()
    assert len(exps) == 8
    assert sum(e["es_ganador"] for e in exps) == 1
    imp = cargar_importancia_variables()
    assert len(imp) == 10
    assert abs(sum(i["importance"] for i in imp) - 100.0) < 0.5


def test_revision_stock_solo_demanda_alta() -> None:
    resumen = predecir_desglose_tienda("Lower Manhattan", "2023-06-26", 24.0, 15.0)
    alertas = items_revision_stock(resumen["desglose"])
    assert all(a["nivel_demanda"] == "Demanda Alta" for a in alertas)


def test_recomendaciones_coherentes_con_su_categoria() -> None:
    """La demanda por producto nunca supera a su categoría y los productos existen en Maven."""
    resumen = predecir_desglose_tienda("Lower Manhattan", "2023-06-26", 24.0, 15.0)
    cat = {d["categoria"]: d["unidades_estimadas"] for d in resumen["desglose"]}
    recs = generar_recomendaciones_turno("Lower Manhattan", "2023-06-26", resumen["desglose"])
    suma_bakery = sum(r["demanda_num"] for r in recs if r["categoria"] == "Bakery")
    assert suma_bakery <= cat["Bakery"] + 1
    for r in recs:
        if "kg" not in r["demanda_estimada"]:
            assert r["demanda_num"] <= cat[r["categoria"]] + 1, r["producto"]
        assert r["cant_sugerida_num"] >= r["demanda_num"]


def test_exportaciones_csv_utf8_bom() -> None:
    """Los CSV del header llevan BOM (acentos correctos en Excel) y suman lo mismo que el KPI."""
    import io

    import pandas as pd

    from ui.pages import export_csv

    resumen = predecir_desglose_tienda("Astoria", "2023-06-26", 24.0, 15.0)
    state = {"store_summary": resumen, "store_location": "Astoria", "fecha_str": "2023-06-26"}
    for pagina in ["Resumen operativo", "Pronóstico de demanda", "Recomendaciones de inventario", "Estado de datos y modelo"]:
        data = export_csv(pagina, state)
        assert data[:3] == b"\xef\xbb\xbf", pagina
        assert len(pd.read_csv(io.BytesIO(data), encoding="utf-8-sig")) > 0, pagina
    df = pd.read_csv(io.BytesIO(export_csv("Resumen operativo", state)), encoding="utf-8-sig")
    assert abs(df["unidades_estimadas"].sum() - resumen["total_unidades_estimadas"]) < 0.5


def test_serie_grafica1_14_dias_historicos() -> None:
    """Gráfica 1 (Entrega 2): 14 días reales + 7 de pronóstico."""
    from services.backend_bridge import predecir_serie_temporal

    serie = predecir_serie_temporal("Lower Manhattan", "Coffee", "2023-06-26", 24.0, 15.0, dias_hist=14, dias_futuro=7)
    assert (serie["tipo"] == "Histórico real").sum() == 14
    assert (serie["tipo"] == "Pronóstico").sum() == 7


if __name__ == "__main__":
    test_contrato_desacoplado_y_latencia_rnf01_rnf03()
    test_manejo_entradas_invalidas_rnf02()
    test_casos_demo_rf05()
    test_desglose_y_tablas_operativas()
    test_curva_horaria_usa_perfil_real_y_rango_del_modelo()
    test_resumen_historico_coincide_con_csv()
    test_experimentos_e_importancias_desde_artefactos()
    test_revision_stock_solo_demanda_alta()
    test_recomendaciones_coherentes_con_su_categoria()
    test_exportaciones_csv_utf8_bom()
    test_serie_grafica1_14_dias_historicos()
    print("ALL_FRONTEND_TESTS_PASSED_100%")
