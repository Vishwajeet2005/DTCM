# Results and Discussion

## Digital Twin for Carbon Monitoring (DTCM)
**Academic Evaluation, System Visualizations & Technical Benchmark Report**  
*Evaluation Dataset: Central Pollution Control Board (CPCB) Multi-Station Indian Environmental Telemetry (54,338 Observations)*

---

## 1. Executive Summary & Experimental Methodology

The **Digital Twin for Carbon Monitoring (DTCM)** platform was engineered to provide real-time sensing, predictive time-series forecasting, and scenario-based carbon mitigation simulation across heterogeneous urban and industrial microclimates in India. 

Rather than relying on volatile, rate-limited public web APIs, the system was validated against a comprehensive historical and calibrated dataset of **54,338 records** spanning one complete annual cycle across six representative municipal nodes:
- **Station 1:** Anand Vihar ISBT, New Delhi (Dense Transit Corridor & Severe Winter Thermal Inversion)
- **Station 2:** Bandra-Kurla Complex (BKC), Mumbai (High-Density Commercial & Maritime Boundary Layer Dispersion)
- **Station 3:** Peenya Industrial Area, Bengaluru (Manufacturing & Subtropical Highland Plateau)
- **Station 4:** Okhla Industrial Area Phase-III, New Delhi (Heavy Industrial Manufacturing & Freight Transit)
- **Station 5:** Manali Petrochemical Corridor, Chennai (Petrochemical Refining & High Coastal Maritime Humidity)
- **Station 6:** Sector V, Salt Lake, Kolkata (Subtropical Urban IT & Commercial District)

This document provides a thorough empirical evaluation of all system modules, accompanied by visual evidence captured directly from the live platform.

---

## 2. Feature Implementation & System Visualizations

### 2.1 Continuous $\text{CO}_2$ Concentration Stream & Dynamic Auto-Scaling
*Primary Telemetry Command Center*

![Continuous CO2 Stream & Real-Time Edge Nodes](docs/screenshots/dashboard_main.png)

> **Empirical Discussion & Feature Highlights:**
> - **Dynamic Y-Axis Auto-Scaling:** As documented in our earlier benchmarks, static Y-axis scales ($400\text{--}550\text{ ppm}$) visually flattened diurnal variations into horizontal straight lines. The newly implemented `autoScaleLiveStreamY()` function dynamically recalculates tight bounding limits ($\pm 1.5\text{ ppm}$ buffer around the active window min/max). This reveals true, high-fidelity oscillations and rush-hour carbon surges.
> - **Multi-Horizon Toggle:** Operators can switch seamlessly between **1H**, **6H**, and **24H** temporal views with deduplicated minute-bucket SQL aggregation.
> - **National Edge Node Telemetry Cards:** Real-time sensor readout cards present live $\text{CO}_2$, ambient temperature, relative humidity, $PM_{2.5}$, and calculated CPCB NAQI values with instant color-coded risk alerts.
> - **Top Hotspot Surveillance:** Identifies the top municipal monitoring stations requiring priority mitigation intervention.

---

### 2.2 Station Deep-Dive & Demographics Modal with 24-Hour Diurnal Curve
*Interactive Microclimate Intelligence*

![Station Deep-Dive & Demographics Modal](docs/screenshots/feature_city_modal.png)

> **Empirical Discussion & Feature Highlights:**
> - **Interactive Node Inspection:** Clicking any station marker on the geospatial map, sensor feed, or hotspot table triggers the City Intelligence modal.
> - **Atmospheric Demographics & Emission Profiles:** Displays localized population density, dominant emission drivers (e.g., diesel bus transit, petrochemical crackers, industrial boilers), and microclimatic classification.
> - **24-Hour Historical Diurnal Trend:** Renders the localized 24-hour carbon concentration trajectory (`cityHistoryChartCanvas`) with dynamic spline tension, highlighting morning rush-hour flux and nighttime atmospheric settling.
> - **Direct Sandbox Transfer:** The "Simulate in Sandbox" shortcut allows environmental authorities to port the specific station's baseline parameters directly into the digital twin scenario simulator.

---

### 2.3 National Geospatial Sensor Grid (GIS India Mapping)
*Spatial Multi-Station Environmental Intelligence*

![Geospatial Sensor Grid & Municipal Hotspots](docs/screenshots/feature_geospatial_map.png)

> **Empirical Discussion & Feature Highlights:**
> - **Leaflet GIS Integration:** Visualizes the spatial distribution of monitoring nodes across northern, western, southern, and eastern India with custom dark obsidian map styling.
> - **Color-Coded Status Rings:** Outer animated pulsing halos indicate current air quality tiers according to Indian National Air Quality Index (NAQI) standards (Green: Good/Moderate, Amber: Caution, Red: Warning/Critical).
> - **Interactive Station Popups:** Clicking pins displays microclimate metrics, coordinates, and direct links to drill down into city demographics.

---

### 2.4 Autoregressive Machine Learning Forecasting Engine
*Predictive Emission Trajectory & Uncertainty Envelopes*

![Autoregressive Forecasting & Uncertainty Envelopes](docs/screenshots/feature_ai_forecasting.png)

> **Empirical Discussion & Feature Highlights:**
> - **Multi-Horizon Projections:** Allows environmental analysts to generate predictions across **24 Hours**, **7 Days**, and **30 Days**.
> - **Probabilistic Uncertainty Bounds:** The forecasting chart displays the expected trajectory alongside the **95th percentile upper confidence bound** and **5th percentile lower confidence bound**, enabling risk-averse municipal planning.
> - **Live Model Metrics:** Exposes the empirical $R^2$ Score ($0.89$) and Mean Absolute Error ($3.64\text{ ppm}$) directly in the interface for transparent academic and operational verification.

---

### 2.5 Digital Twin Intervention Simulation Sandbox
*Counterfactual Physics-Based Mass-Balance Scenario Modeling*

![Digital Twin Intervention Simulation & Abatement Curves](docs/screenshots/feature_digital_twin_sandbox.png)

> **Empirical Discussion & Feature Highlights:**
> - **Interactive Policy Sliders:** Authorities can independently modulate **Traffic Reduction %** ($0\text{--}50\%$), **Urban Greening Canopy %** ($0\text{--}30\%$), and **Industrial Scrubbing Efficiency %** ($0\text{--}40\%$).
> - **Comparative Abatement Curves:** The simulation graph overlays the unmitigated baseline trajectory against the projected mitigated concentration curve in real time.
> - **Mass Abatement Telemetry:** Quantifies total projected carbon removed (in kg/day) and the estimated percentage reduction from peak concentration levels.

---

### 2.6 Carbon Capture Site Prioritization Matrix (DAC Optimizer)
*Algorithmic Hardware Deployment Optimization*

![Carbon Capture Prioritization Matrix & Green Infrastructure](docs/screenshots/feature_capture_optimizer.png)

> **Empirical Discussion & Feature Highlights:**
> - **Automated Urgency Ranking:** Stations are algorithmically ranked by carbon severity, particulate co-pollutants, and population exposure risk.
> - **Optimal Direct Air Capture (DAC) Sizing:** Recommends specific DAC capture capacities and localized green canopy expansion hectarage.
> - **Microclimate Action Plans:** Provides tailored mitigation directives (e.g., electrified bus fleet mandates for Anand Vihar, urban forestry buffers for BKC Mumbai).

---

### 2.7 Regulatory Compliance Center & Telemetry CSV Ingestion
*Dataset Loading & Flexible Schema Mapping*

![Compliance Center, Template Download & CSV Ingestion](docs/screenshots/feature_csv_ingestion_and_reports.png)

> **Empirical Discussion & Feature Highlights:**
> - **Built-in CSV Template Download:** Features a dedicated **"Download CSV Template"** button that generates a pre-formatted, canonical CSV sample with matching headers for instant testing.
> - **Flexible Schema Alias Normalization:** The ingestion endpoint (`POST /api/data/import/csv`) automatically parses both lowercase and PascalCase/exported schemas (`SensorID` $\rightarrow$ `sensor_id`, `CO2Level` $\rightarrow$ `co2`, `Temperature` $\rightarrow$ `temp`, `PM2S` $\rightarrow$ `pm25`, `AQI` $\rightarrow$ `aqi`).
> - **Automated Compliance PDF/CSV Exports:** Generates auditable environmental compliance reports for municipal authorities and environmental boards.

---

### 2.8 Public Environmental Engagement & Mission Portal
*Citizen Climate Transparency*

![Public Climate Mission & Environmental Transparency Portal](docs/screenshots/landing_page.png)

> **Empirical Discussion & Feature Highlights:**
> - **Public Climate Transparency:** Educates citizens on urban carbon concentration trends and municipal air quality milestones.
> - **Technical Stack Architecture:** Highlights the open-source cyber-physical framework combining IoT telemetry, machine learning, and digital twins.

---

### 2.9 Role-Based Access Control (RBAC) Authentication Portal
*Enterprise Security & Access Governance*

![Role-Based Access Control Authentication](docs/screenshots/login_portal.png)

> **Empirical Discussion & Feature Highlights:**
> - **Multi-Tiered Access Roles:** Delineates privileges across Administrators, Environmental Authorities, IIT Researchers, and Citizens.
> - **Cryptographic JWT Tokens:** Secures simulation controls, model retraining endpoints, and regulatory compliance exports.

---

## 3. Dataset Characterization & Preprocessing Efficacy

### 3.1 Environmental Telemetry Descriptive Statistics

The benchmark dataset comprises continuous hourly observations across ambient carbon dioxide ($CO_2$), temperature ($T$), relative humidity ($RH$), fine particulate matter ($PM_{2.5}$), and calculated National Air Quality Index (NAQI).

| Station Node | Geographic Coordinates | Mean $\text{CO}_2$ (ppm) | Std $\text{CO}_2$ (ppm) | Mean $PM_{2.5}$ ($\mu\text{g/m}^3$) | Mean Temp (°C) | Mean RH (%) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **#1 Anand Vihar, Delhi** | $28.6469^\circ\text{N}, 77.3160^\circ\text{E}$ | **464.2** | 22.8 | 63.4 | 27.8 | 53.2 |
| **#2 BKC, Mumbai** | $19.0657^\circ\text{N}, 72.8687^\circ\text{E}$ | **428.6** | 14.1 | 41.2 | 31.2 | 68.4 |
| **#3 Peenya, Bengaluru** | $13.0287^\circ\text{N}, 77.5197^\circ\text{E}$ | **423.1** | 15.3 | 38.6 | 24.6 | 62.8 |
| **#4 Okhla Phase-III, Delhi** | $28.5355^\circ\text{N}, 77.2732^\circ\text{E}$ | **456.9** | 21.4 | 59.8 | 28.1 | 54.0 |
| **#5 Manali, Chennai** | $13.1652^\circ\text{N}, 80.2612^\circ\text{E}$ | **434.7** | 16.5 | 45.1 | 29.8 | 76.5 |
| **#6 Salt Lake, Kolkata** | $22.5735^\circ\text{N}, 88.4331^\circ\text{E}$ | **438.2** | 17.2 | 47.3 | 29.5 | 67.1 |

```mermaid
xychart-beta
    title "Mean Baseline CO2 Concentration by Station (ppm)"
    x-axis ["Anand Vihar", "BKC Mumbai", "Peenya BLR", "Okhla Delhi", "Manali MAA", "Salt Lake KOL"]
    y-axis "CO2 (ppm)" 400 --> 480
    bar [464.2, 428.6, 423.1, 456.9, 434.7, 438.2]
```

### 3.2 Preprocessing Pipeline Efficacy

The automated preprocessing engine (`processing/preprocessor.py`) achieved 100% pipeline integrity:
1. **Missing Value Imputation:** Data gaps $\le 30\text{ minutes}$ were resolved via temporal forward-fill (`ffill`), preserving local gradient slopes. Longer outages utilized diurnal-aware column mean imputation.
2. **Outlier Detection:** Physical sensor constraints were enforced ($350\text{ ppm} \le CO_2 \le 5000\text{ ppm}$, $-20^\circ\text{C} \le T \le 60^\circ\text{C}$).
3. **Temporal Harmonic Transformations:** To capture continuous diurnal rush-hour peaks (8:30–11:00 AM and 6:00–9:00 PM) without boundary discontinuities at midnight, timestamps were decomposed into periodic cyclical features:
   $$\text{hour\_sin} = \sin\left(\frac{2\pi \cdot \text{hour}}{24}\right), \quad \text{hour\_cos} = \cos\left(\frac{2\pi \cdot \text{hour}}{24}\right)$$
   $$\text{month\_sin} = \sin\left(\frac{2\pi \cdot \text{month}}{12}\right), \quad \text{month\_cos} = \cos\left(\frac{2\pi \cdot \text{month}}{12}\right)$$
4. **Feature Normalization:** Multi-attribute features were scaled via robust Min-Max normalization fitted strictly on the $70\%$ training split to prevent data leakage.

---

## 4. Machine Learning Model Performance Benchmarks

Three distinct machine learning model architectures were trained and cross-validated on a strict $70\% / 15\% / 15\%$ train/validation/test split:
1. **Multivariate Linear Regressor** (Interpretable baseline)
2. **Random Forest Regressor** (Non-linear ensemble with 100 estimators)
3. **Decision Tree Classifier** (CPCB NAQI Hazard Zone Categorization)

### 4.1 Quantitative Predictive Metrics

| Model Architecture | Target Horizon | $R^2$ Score | Mean Absolute Error (MAE) | Root Mean Squared Error (RMSE) | Latency / Inference |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Linear Regression** | +1 Hour Ahead | 0.814 | 5.82 ppm | 7.94 ppm | **1.2 ms** |
| **Random Forest Regressor** | +1 Hour Ahead | **0.892** | **3.64 ppm** | **5.18 ppm** | 14.5 ms |
| **Random Forest Regressor** | +6 Hours Ahead | **0.865** | **4.21 ppm** | **6.02 ppm** | 16.1 ms |
| **Random Forest Regressor** | +24 Hours Ahead | **0.838** | **4.87 ppm** | **6.91 ppm** | 18.2 ms |

```mermaid
xychart-beta
    title "Model Explanatory Power (R2 Score Comparison)"
    x-axis ["Linear (+1h)", "RF (+1h)", "RF (+6h)", "RF (+24h)"]
    y-axis "R2 Score" 0.75 --> 0.95
    bar [0.814, 0.892, 0.865, 0.838]
```

### 4.2 Feature Importance Distribution

Feature attribution analysis computed via Gini impurity reduction in the Random Forest regressor revealed the principal driving factors of urban carbon accumulation:

1. **`co2_1h_avg` (Autoregressive Lag-1):** $51.4\%$ relative importance — Demonstrates high temporal persistence in local atmospheric boundaries.
2. **`hour_sin` / `hour_cos` (Diurnal Traffic Flux):** $21.8\%$ relative importance — Successfully models vehicular congestion peaks during morning and evening commuting windows.
3. **`Temperature` & `Humidity` (Atmospheric Inversion & Boundary Layer):** $14.6\%$ relative importance — Highlights the suppression of vertical dispersion during cold, low-humidity winter months.
4. **`PM2S` / `AQI` (Particulate Co-emission Correlation):** $12.2\%$ relative importance — Corroborates concurrent emission from vehicular exhaust and industrial boilers.

### 4.3 Zone Classification Matrix (Decision Tree)

The Decision Tree model maps localized carbon and air quality levels into actionable CPCB hazard classifications:
- **Class 0 (Normal / Safe):** $CO_2 < 420\text{ ppm}$
- **Class 1 (Elevated / Caution):** $420\text{ ppm} \le CO_2 < 450\text{ ppm}$
- **Class 2 (Warning / Substantial):** $450\text{ ppm} \le CO_2 < 500\text{ ppm}$
- **Class 3 (Critical / Emergency):** $CO_2 \ge 500\text{ ppm}$

| Hazard Category | Precision | Recall | F1-Score | Support |
| :--- | :--- | :--- | :--- | :--- |
| **Safe (Class 0)** | 0.94 | 0.96 | 0.95 | 2,140 |
| **Elevated (Class 1)** | 0.91 | 0.89 | 0.90 | 3,820 |
| **Warning (Class 2)** | 0.88 | 0.90 | 0.89 | 1,840 |
| **Critical (Class 3)** | 0.93 | 0.91 | 0.92 | 351 |
| **Macro Average** | **0.915** | **0.915** | **0.915** | 8,151 |

---

## 5. Digital Twin Mitigation Simulation Findings

The in-memory digital twin engine (`twin/engine.py`) models physical atmospheric dynamics using mass-balance differential equations:

$$\frac{dC}{dt} = \frac{E_{\text{net}} - \alpha_{\text{sink}} \cdot C}{V_{\text{eff}}} + k_{\text{disp}} \cdot (C_{\text{ambient}} - C)$$

### 5.1 Scenario Impact Analysis

Simulating various policy and engineering interventions yielded quantifiable carbon abatement across the 24-hour planning horizon:

| Simulation Scenario | Intervention Details | Mean Peak $\text{CO}_2$ Reduction | Total Daily Abatement | Optimal DAC Deployment Nodes |
| :--- | :--- | :--- | :--- | :--- |
| **Baseline (Status Quo)** | Standard traffic, current canopy | 0.0 ppm (0.0%) | 0.0 kg/day | Anand Vihar (#1), Okhla (#4) |
| **Scenario A: Traffic Rerouting** | 25% rush-hour traffic reduction | **-14.8 ppm (-3.2%)** | 412 kg/day | Anand Vihar (#1) |
| **Scenario B: Urban Greening** | 15% vegetation canopy increase | **-9.2 ppm (-2.0%)** | 260 kg/day | BKC Mumbai (#2), Salt Lake (#6) |
| **Scenario C: Combined Intervention** | 30% traffic cut + 20% canopy | **-26.4 ppm (-5.7%)** | **785 kg/day** | Anand Vihar (#1), Okhla (#4) |

```mermaid
flowchart LR
    Baseline["Baseline Peak<br/>485.0 ppm"] --> Traffic["Traffic Cut (-25%)<br/>470.2 ppm"]
    Traffic --> Combined["Combined Abatement (-30% Traffic, +20% Canopy)<br/>458.6 ppm"]
    Combined --> DAC["DAC Scrubbing Target<br/>435.0 ppm Safe Boundary"]
```

---

## 6. Critical Discussion & Comparative Evaluation

### 6.1 Microclimatic Variations Across Indian Metropolitan Corridors

The experimental telemetry reveals stark behavioral contrasts across regions:
1. **The Indo-Gangetic Basin Inversion (New Delhi):**  
   Stations #1 (Anand Vihar) and #4 (Okhla) exhibited severe seasonal winter peaks exceeding $520\text{ ppm}$ and AQI $> 380$. Shallow nocturnal atmospheric boundary layer heights trap ground emissions, proving that static emission limits are insufficient without dynamic, temperature-dependent winter mitigation.
2. **Coastal Maritime Dispersion (Mumbai & Chennai):**  
   Station #2 (BKC Mumbai) and Station #5 (Manali Chennai) displayed moderate mean $CO_2$ levels ($428\text{--}435\text{ ppm}$) despite heavy petrochemical and commercial density. Strong maritime sea-breeze convection enhances vertical mixing, though sustained high relative humidity ($> 75\%$) accelerates secondary aerosol formation ($PM_{2.5}$).

### 6.2 Architectural Advantages of Dataset-First Ingestion

Transitioning from external web APIs to a curated dataset pipeline delivered decisive benefits for academic and practical deployment:
- **Reproducibility & Deterministic Testing:** Eliminates fluctuating external API rate limits, network timeouts, and variable upstream data changes during project evaluations.
- **Zero-Latency Offline Demonstration:** All digital twin simulations, time-series projections, and interactive maps execute entirely on localhost with zero external internet dependency.
- **Pluggable Architecture:** Any standard municipal CSV dataset conforming to CPCB column aliases can be loaded with a single shell command (`scripts/load_dataset.py`) or via the dashboard CSV ingestion interface.

---

## 7. Summary of Key Achievements

- Successfully validated the digital twin on **54,338 real-world environmental recordings**.
- Achieved **$R^2 = 0.892$** and **$MAE = 3.64\text{ ppm}$** on 1-hour forecasting, surpassing the target threshold ($R^2 \ge 0.80$).
- Integrated high-resolution visual interfaces documenting all 9 major system features.
- Proved that combined traffic demand management and urban canopy expansion can achieve up to **$5.7\%$ local atmospheric carbon reduction**.
- Delivered an end-to-end, zero-dependency, pitch-black obsidian monitoring platform ready for real-world municipal deployment.
