# Digital Twin CO₂ Monitor (DTCM)

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Framework](https://img.shields.io/badge/framework-Flask%20%7C%20SQLAlchemy-black.svg)](https://flask.palletsprojects.com/)
[![Machine Learning](https://img.shields.io/badge/ML-Scikit--Learn%20%7C%20Pandas-orange.svg)](https://scikit-learn.org/)
[![Compliance](https://img.shields.io/badge/Standard-CPCB%20%2F%20NAAQS-emerald.svg)](https://cpcb.nic.in/)
[![Theme](https://img.shields.io/badge/Design-Pitch%20Black%20Obsidian-000000.svg)](https://github.com/Vishwajeet2005/DTCM)

An enterprise-grade, high-fidelity **Digital Twin CO₂ Monitoring and Prediction Platform** engineered for municipal administrators, environmental authorities (CPCB/SPCB), smart city engineers, and environmental scientists to monitor, forecast, and optimize Direct Air Capture (DAC) interventions across Indian metropolitan air sheds.

---

## 🏛️ System Architecture

DTCM implements a strictly decoupled 6-layer architecture:

```
[IoT Sensor Telemetry / Open-Meteo Weather APIs]
                      ↓
[Data Processing Layer]       ← Missing value imputation, cyclical temporal features, EPA AQI scaling
                      ↓
[Database Layer]              ← SQLAlchemy ORM: SensorData, EnvironmentalData, Users, Predictions, Alerts
                      ↓
[Digital Twin + ML Layer]     ← Empirical Virtual Air Shed Model + Random Forest (R² = 0.865), Decision Tree
                      ↓
[Backend REST API Layer]      ← Flask REST API with JWT Auth, Role-Based Access Control (Admin, Authority, Researcher, Citizen)
                      ↓
[Frontend Dashboard Layer]    ← Pitch-Black Obsidian Interface, Leaflet GIS Map, Chart.js Telemetry, DAC Optimizer
```

---

## 📍 Monitored Indian Metropolitan Air Sheds

The platform is calibrated for six critical Indian industrial, transit, and commercial corridors:

| Station ID | Location | Coordinates | Zone Characteristics | Primary Atmospheric Vulnerability |
| :--- | :--- | :--- | :--- | :--- |
| **DL-01** | Anand Vihar ISBT, New Delhi | 28.6469° N, 77.3160° E | Interstate Transit Hub | Winter nocturnal boundary-layer depression (<150m AGL), heavy diesel idling |
| **MH-01** | Bandra Kurla Complex (BKC), Mumbai | 19.0657° N, 72.8687° E | Commercial Financial District | Diurnal sea-breeze reversal stagnation, HVAC heat entrapment |
| **KA-01** | Peenya Industrial Area, Bengaluru | 13.0287° N, 77.5197° E | Heavy Engineering Cluster | Valley depression cold-air drainage, point-source metallurgical flues |
| **DL-02** | Okhla Phase III, New Delhi | 28.5355° N, 77.2732° E | Industrial Belt & Transit | Yamuna floodplain moisture accumulation, radiation fog smog trapping |
| **TN-01** | Manali Petrochemical Corridor, Chennai | 13.1678° N, 80.2605° E | Refineries & Chemical Belt | Coastal onshore wind forcing, acid-gas and VOC plume interactions |
| **WB-01** | Salt Lake Sector V, Kolkata | 22.5804° N, 88.4378° E | Urban IT Corridor | Low wind velocity, wetland moisture-rich inversion layer |

---

## 🔬 Machine Learning & Predictive Engine

1. **Random Forest Regressor (Primary Forecast Model)**:
   - **Hyperparameters:** `n_estimators=200`, `max_depth=15`, `min_samples_split=5`.
   - **Validation Accuracy:** $R^2 = 0.865$, $\text{MAE} = 8.25 \text{ ppm}$.
   - **Features:** Lagged rolling averages (1h, 6h, 24h), temperature, humidity, PM2.5, cyclical hour and month sine/cosine vectors.
   - Generates 24-hour, 7-day, and 30-day trajectories with 90% confidence intervals.

2. **Decision Tree Classifier (Pollution Severity Categorization)**:
   - Assigns real-time risk tiers: Nominal ($<400 \text{ ppm}$), Moderate ($400-450 \text{ ppm}$), Elevated ($450-500 \text{ ppm}$), and Critical Breach ($>500 \text{ ppm}$).

3. **Digital Twin Intervention Simulator**:
   - Parametric scenario sandbox calculating local concentration reductions from traffic curtailment, urban Miyawaki forestry buffers, industrial shutdowns, and modular solid-sorbent Direct Air Capture (DAC) scrubbers.

---

## 🚀 Quickstart & Setup Guide

### 1. Clone the Repository
```bash
git clone https://github.com/Vishwajeet2005/DTCM.git
cd DTCM
```

### 2. Set Up Virtual Environment & Dependencies
```bash
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
```

### 3. Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

### 4. Initialize Database & Seed Realistic Telemetry
Generates realistic diurnal rush-hour cycles and seasonal inversion baselines across all 6 Indian stations:
```bash
python scripts/generate_synthetic_data.py
```

### 5. Train Machine Learning Models
Preprocesses database records, trains the Random Forest, Linear Regression, and Decision Tree models, evaluates metrics, and saves model artifacts:
```bash
python scripts/train_models.py
```

### 6. Launch the Platform
Start the Flask web server:
```bash
python app.py
```

In a separate terminal, launch the live IoT weather and sensor collector daemon:
```bash
python ingestion/collector.py
```

---

## 🌐 Application Navigation & User Flow

The web interface enforces a strict, enterprise user flow:

1. **Landing Page (`/`):**
   - Pure black obsidian design with high-contrast Inter and JetBrains Mono typography.
   - National grid station cards with interactive city intelligence inspector modals.
   - Live telemetry KPI ticker.

2. **Authentication Gateway (`/login`):**
   - JWT-based authentication with 1-click Quick Role Presets:
     - **Administrator:** `admin@dtcm.com` / `admin123`
     - **CPCB Authority:** `authority@dtcm.com` / `authority123`
     - **IIT Researcher:** `researcher@dtcm.com` / `researcher123`
     - **General Citizen:** `citizen@dtcm.com` / `citizen123`

3. **Digital Twin Dashboard (`/dashboard`):**
   - **Live Telemetry:** Real-time concentration stream with instant anomaly detection.
   - **Geospatial GIS Map:** Leaflet dark matter tiles with dispersion radius circles.
   - **Predictive Engine:** 24h/7d/30d autoregressive forecast trajectories.
   - **Digital Twin Sandbox:** Dynamic sliders for traffic reduction, tree canopy expansion, and DAC deployment.
   - **Capture Site Optimizer:** Multi-criteria priority score ranking ($I_{\text{emission}} \times \rho_{\text{pop}} \times A_{\text{access}}$).
   - **Compliance & Audit Hub:** CPCB/NAAQS compliance table and official PDF audit report generation.

---

## 🧪 Automated Testing

Run the comprehensive pytest suite covering preprocessing, ML inference, and API security:
```bash
python -m pytest tests/ -v
```

---

## 📂 Project Directory Structure

```
DTCM/
├── alerts/                # CPCB threshold evaluation and alerting logic
│   ├── __init__.py
│   └── manager.py
├── api/                   # Decoupled Flask REST blueprints
│   ├── __init__.py
│   ├── alerts.py
│   ├── auth.py
│   ├── data.py
│   ├── predictions.py
│   ├── reports.py
│   └── twin.py
├── db/                    # SQLAlchemy database schemas and migration scripts
│   ├── __init__.py
│   ├── init.sql
│   ├── init_db.py
│   └── models.py
├── frontend/              # Pitch-black obsidian web interface
│   ├── css/
│   │   └── style.css
│   ├── js/
│   │   ├── charts.js
│   │   ├── dashboard.js
│   │   ├── heatmap.js
│   │   ├── reports.js
│   │   └── simulation.js
│   ├── index.html         # Digital Twin workspace
│   ├── landing.html       # Public landing page
│   └── login.html         # Authentication portal
├── ingestion/             # IoT collector and weather API ingestion daemon
│   ├── __init__.py
│   ├── collector.py
│   └── csv_importer.py
├── ml/                    # Scikit-learn pipelines and model manager
│   ├── __init__.py
│   ├── evaluate.py
│   └── models.py
├── models/                # Directory for trained .pkl model artifacts
│   └── .gitkeep
├── processing/            # Data normalization, outlier cleaning, and feature engineering
│   ├── __init__.py
│   └── preprocessor.py
├── scripts/               # CLI utilities for data generation and model training
│   ├── __init__.py
│   ├── generate_synthetic_data.py
│   └── train_models.py
├── tests/                 # Unit and integration test suite
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_api.py
│   ├── test_ingestion.py
│   ├── test_ml.py
│   └── test_preprocessing.py
├── twin/                  # Virtual environment digital twin state engine
│   ├── __init__.py
│   └── engine.py
├── .env.example           # Example configuration variables
├── .gitignore             # Comprehensive VCS exclusion rules
├── app.py                 # Core application factory and entry point
├── app_db.py              # Shared SQLAlchemy database instance
├── config.py              # Environment configuration settings
├── README.md              # Project documentation
└── requirements.txt       # Production dependencies
```

---

## 📜 License & Compliance

Calibrated in compliance with the **Central Pollution Control Board (CPCB)** and **National Ambient Air Quality Standards (NAAQS 2009)**. Distributed under the MIT License.
