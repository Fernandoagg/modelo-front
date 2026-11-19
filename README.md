# CaféSmart AI — Frontend Operativo (`modelo-front`)

Interfaz gráfica interactiva desarrollada en **Streamlit + Plotly** conforme a los mockups de alta fidelidad de **Figma (`IA-CafeSmart`)** y las especificaciones técnicas de las **Entregas 2, 3 y 4**.

## Arquitectura Desacoplada (Multi-Repo / Carpetas Independientes)

Siguiendo el requerimiento no funcional **RNF-03 (Desacoplamiento de Código)**, el frontend vive en su propia carpeta independiente (`D:\modelo\modelo-front`) separada del backend (`D:\modelo\modelo`):

- **Frontend (`D:\modelo\modelo-front`)**: Contiene exclusivamente la capa de presentación (`app.py`, `ui/theme.py`, `ui/shell.py`, `ui/pages_*.py`, `ui/charts.py`, `assets/`) y el conector (`services/backend_bridge.py`).
- **Backend (`D:\modelo\modelo`)**: Contiene el pipeline de datos, los artefactos serializados (`models/modelo_candidato.joblib`, `models/scaler.joblib`, `models/feature_defaults.json`) y expone el contrato `predecir(entrada: dict)` en `src/models/predict.py`.

## Pantallas de Alta Fidelidad Incluidas (Figma)

1. **Propósito e Incorporación (`#21:2`)**: Contexto ejecutivo del proyecto, arquitectura desacoplada, integrantes del equipo LITIID 72 e inspector en vivo del contrato JSON `predecir(entrada: dict)`.
2. **Resumen operativo (`#21:5677`)**: Tarjetas KPI ejecutivas (Ref. Histórico, Demanda Estimada, Mayor Volumen Previsto, Revisión de Stock y Meteorología), gráfica comparativa por franja horaria (`06:00 - 20:00 hrs`) y diaria, contexto climático y recomendación destacada del turno.
3. **Pronóstico de demanda (`#21:4616`)**: Consola de consulta multivariada, tarjetas Bento de horizonte 7 días, mosaico visual de insumos clave (granos tueste medio y bollería matutina), las 3 gráficas dinámicas del catálogo (Serie histórica vs. pronóstico con banda al 85%, Distribución por categoría y Scatter Plot de sensibilidad al clima) y tabla detallada por franja horaria con exportación `.CSV`.
4. **Recomendaciones de inventario (`#21:4007`)**: 3 bloques Bento de preparación matutina, productos con demanda atípica y diagnóstico de mermas, guía detallada interactiva con checkboxes de calibración en tiempo real y exportación `.CSV`.
5. **Análisis histórico (`#21:3226`)**: Explorador retrospectivo del dataset Maven (`149,116 transacciones` / `214,470 unidades`), evolución semestral con media móvil 7d, estacionalidad por día de la semana, comparativa territorial por sucursal, mix de producto, curva intradía y tabla de rendimiento.
6. **Estado de datos y modelo (`#21:5194`)**: Auditoría técnica de las fuentes de datos, cruce climático estatal de México, resultados comparativos de los 8 experimentos de Machine Learning (`LGBMRegressor (Tweedie)` ganador con `WAPE = 14.86%`), importancia de variables y matriz de componentes del sistema.

## Ejecución

Desde la carpeta `D:\modelo\modelo-front`:

```powershell
streamlit run app.py
```

## Estructura de la interfaz (réplica Figma)

- `ui/theme.py`: tokens de color/tipografía del Figma, CSS global y helpers HTML (`html`, `icon`, `badge`).
- `ui/shell.py`: Aside (navegación + sucursal activa) y Header fijo (sucursal, semana → panel de simulación RF-01/02/05, clima, exportar).
  Varios widgets comparten el mismo estado maestro mediante `bound()` (sin modificar keys de widgets ya instanciados).
- `ui/pages_*.py`: una vista por archivo (proposito, resumen, pronostico, recomendaciones, historico, estado).
- `assets/`: fotos y avatar extraídos de los PDF de Figma + especificación técnica (Entrega 2) descargable.

## Cumplimiento de la especificación (Entrega 2 / 3)

| Requisito | Dónde se cumple |
|---|---|
| RF-01 Formulario de entradas | Barra lateral → *Controles de predicción* (y panel *Semana* del header) |
| RF-02 Disparador de inferencia | Botón *Calcular predicción (RF-02)*; la app re-infiere en cada cambio (< 3 s) |
| RF-03 KPIs + semáforo + confiabilidad | Resumen: demanda, semáforo Baja/Habitual/Alta (verde/ámbar/rojo), MAPE y WAPE del modelo |
| RF-04 Filtros reactivos | Sucursal, categoría y fecha en todas las vistas; filtros propios en Histórico |
| RF-05 Casos precargados | *Caso de demostración* + *Cargar caso* |
| RNF-01 Latencia | Re-ejecución típica 0.5–2 s por vista |
| RNF-02 Entradas inválidas | `st.warning`/`st.error` (fechas fuera de ventana, Tmáx < Tmín) sin romper la sesión |
| RNF-03 Desacoplamiento | El front solo consume `predecir()` vía `services/backend_bridge.py` |
| Gráficas 1-3 | Serie 14 d reales + 7 d pronóstico con banda 85%, barras por categoría, dispersión clima |
| Exportación CSV | UTF-8 con BOM (acentos correctos en Excel); *Exportar reporte* exporta la vista activa |

> Fuera de alcance según la Entrega 2 (Exclusión 2): pronóstico por SKU y horario. La app muestra una
> **desagregación** por producto/hora usando participaciones históricas reales, indicada como tal en la UI.
