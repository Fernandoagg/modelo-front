# CaféSmart AI — Frontend Operativo

Aplicación web interactiva desarrollada en **Python (Streamlit + Plotly)** para el pronóstico de demanda diaria, recomendaciones de inventario, análisis histórico y monitoreo del modelo predictivo de **CaféSmart AI**.

El frontend opera de forma desacoplada consumiendo el motor de inferencia y los artefactos entrenados del repositorio de backend (`modelo`).

---

## 1. Versiones Exactas de Python y Frameworks Utilizados

El sistema fue desarrollado y validado con las siguientes versiones exactas:

| Componente | Versión validada | Restricción (`requirements.txt`) | Función |
| :--- | :--- | :--- | :--- |
| **Python** | `3.12.10` | `>=3.12` | Intérprete base |
| **Streamlit** | `1.67.0` | `>=1.38.0` | Framework web interactivo |
| **Plotly** | `7.1.0` | `>=5.24.0` | Visualizaciones dinámicas |
| **Pandas** | `3.1.1` | `>=2.2.0` | Manipulación y agregación tabular |
| **NumPy** | `2.5.4` | `>=1.26.0` | Cálculo numérico |
| **Scikit-learn** | `1.9.1` | `>=1.5.0` | Preprocesamiento y soporte al pipeline ML |
| **LightGBM** | `4.7.0` | `>=4.5.0` | Motor de inferencia del modelo ganador |
| **XGBoost** | `3.4.1` | `>=2.1.0` | Soporte para modelos experimentales |
| **Joblib** | `1.6.0` | `>=1.4.0` | Carga de artefactos serializados (`.joblib`) |

---

## 2. Dependencias Requeridas e Instalación

### Prerrequisito: Disposición del Backend
Este frontend requiere acceso local al repositorio del backend (`modelo`) con sus datos y artefactos entrenados. La forma recomendada es ubicar ambos repositorios en el mismo directorio padre:

```text
directorio-trabajo/
├── modelo/         # Backend de IA (motor de inferencia, modelos y datasets)
└── modelo-front/   # Este repositorio (Frontend Streamlit)
```

> Si el backend se encuentra en otra ruta, consulta la sección [3. Variables de Entorno](#3-variables-de-entorno).

### Instalación paso a paso

1. **Entrar al directorio del frontend:**
   ```bash
   cd modelo-front
   ```

2. **Crear y activar un entorno virtual:**

   - **Windows (PowerShell):**
     ```powershell
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```
   - **Linux / macOS:**
     ```bash
     python3 -m venv .venv
     source .venv/bin/activate
     ```

3. **Instalar las dependencias documentadas en `requirements.txt`:**
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

---

## 3. Variables de Entorno

El sistema funciona **100% de manera local** y **no requiere API keys, tokens ni credenciales de servicios externos**.

La única variable de entorno soportada es **opcional** y únicamente se necesita si la carpeta del backend no está ubicada en `../modelo`:

```env
# .env.example (referencia — no se requieren llaves de API externas)
# Ruta absoluta o relativa hacia la carpeta del backend de CaféSmart AI.
# Valor por defecto si se omite: ../modelo
CAFESMART_BACKEND_DIR=../modelo
```

Para definirla antes de arrancar (solo si el backend está en otra ubicación):

- **Windows (PowerShell):**
  ```powershell
  $env:CAFESMART_BACKEND_DIR = "ruta/al/backend/modelo"
  ```
- **Linux / macOS:**
  ```bash
  export CAFESMART_BACKEND_DIR="/ruta/al/backend/modelo"
  ```

---

## 4. Comando Exacto de Arranque

Con el entorno virtual activado y ubicado en la raíz de `modelo-front`, ejecuta:

```bash
streamlit run app.py
```

Al iniciar, la aplicación quedará disponible en el navegador en:

- **URL local:** `http://localhost:8501`

*(Si el puerto `8501` se encuentra ocupado, puede iniciarse en otro puerto con `streamlit run app.py --server.port 8502`.)*

### Verificación rápida (opcional)
Para validar que la conexión con el backend y la inferencia funcionan correctamente antes o después de abrir la interfaz:

```bash
python tests/test_frontend.py
```

---

## 5. Credenciales de Prueba y Escenarios de Validación

- **Autenticación / Login:** **No aplica.** La aplicación no implementa pantalla de inicio de sesión ni control de acceso; al abrir `http://localhost:8501` se ingresa directamente al panel operativo.
- **Escenarios precargados para pruebas:** En la barra lateral (*Controles de predicción → Caso de demostración*) se incluyen **5 casos precargados** (por ejemplo, lunes operativo en *Lower Manhattan*, día lluvioso en *Astoria* y fin de semana en *Hell's Kitchen*) que permiten probar el modelo inmediatamente con un solo clic en **Cargar caso**.

---

## 6. Solución Rápida de Problemas

| Error común | Causa probable | Solución |
| :--- | :--- | :--- |
| `ModuleNotFoundError: No module named 'src'` | No se encontró la carpeta del backend en `../modelo`. | Verifica que `modelo` esté al mismo nivel que `modelo-front` o configura `CAFESMART_BACKEND_DIR`. |
| `FileNotFoundError` en `models/` o `data/` | Faltan los artefactos entrenados o datasets del backend. | Asegúrate de que el repositorio `modelo` incluya sus archivos en `models/` y `data/`. |
| `Port 8501 is already in use` | Otra instancia de Streamlit está corriendo en el puerto por defecto. | Ejecuta `streamlit run app.py --server.port 8502`. |
