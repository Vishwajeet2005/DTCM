# DTCM Environmental Telemetry Dataset

This directory contains the environmental telemetry datasets used by the **Digital Twin for Carbon Monitoring (DTCM)** platform for offline analytics, time-series forecasting, emission mitigation simulations, and live station telemetry replay.

---

## 1. Primary Dataset Files

| File | Records | File Size | Description |
| :--- | :--- | :--- | :--- |
| `cpcb_indian_stations_telemetry.csv` | **54,338** | **~5.1 MB** | Complete 1-year multi-station telemetry across 6 Indian metropolitan nodes (New Delhi, Mumbai, Bengaluru, Chennai, Kolkata). |
| `sample_telemetry_dataset.csv` | **100** | **~10 KB** | Lightweight sample slice for quick verification, schema inspection, and testing. |

---

## 2. Station Geographic Coverage

The dataset covers critical commercial, industrial, and high-traffic transit corridors conforming to Central Pollution Control Board (CPCB) CAAQMN monitoring standards:

1. **Station #1 — Anand Vihar ISBT, New Delhi** ($28.6469^\circ\text{N}, 77.3160^\circ\text{E}$): Inter-state transit hub characterized by high vehicular density and winter inversion effects.
2. **Station #2 — Bandra-Kurla Complex (BKC), Mumbai** ($19.0657^\circ\text{N}, 72.8687^\circ\text{E}$): Dense commercial business district subject to coastal atmospheric dispersion.
3. **Station #3 — Peenya Industrial Area, Bengaluru** ($13.0287^\circ\text{N}, 77.5197^\circ\text{E}$): High-tech and machinery manufacturing industrial estate with moderate diurnal elevation.
4. **Station #4 — Okhla Industrial Area Phase-III, New Delhi** ($28.5355^\circ\text{N}, 77.2732^\circ\text{E}$): Heavy industrial manufacturing and freight traffic corridor.
5. **Station #5 — Manali Petrochemical Corridor, Chennai** ($13.1652^\circ\text{N}, 80.2612^\circ\text{E}$): Coastal petrochemical and refinery cluster with maritime humidity influences.
6. **Station #6 — Sector V, Salt Lake, Kolkata** ($22.5735^\circ\text{N}, 88.4331^\circ\text{E}$): Urban commercial IT cluster with seasonal subtropical variations.

---

## 3. Schema & Column Definitions

| Column Name | Data Type | Unit | Description |
| :--- | :--- | :--- | :--- |
| `sensor_id` | Integer | ID | Unique identifier for the municipal monitoring station ($1\text{--}6$). |
| `location` | String | Text | Canonical station name and municipal location. |
| `co2` | Float | ppm | Carbon dioxide concentration in parts per million (ambient baseline $\approx 410\text{--}520\text{ ppm}$). |
| `temp` | Float | °C | Ambient dry-bulb air temperature. |
| `humidity` | Float | % | Ambient relative atmospheric humidity ($20\%\text{--}95\%$). |
| `pm25` | Float | $\mu\text{g/m}^3$ | Fine particulate matter ($PM_{2.5}$) concentration. |
| `aqi` | Float | Index | Indian National Air Quality Index (NAQI) value ($0\text{--}500$). |
| `timestamp` | String / Datetime | ISO-8601 | Recording date and time (`YYYY-MM-DD HH:MM:SS`). |

---

## 4. How to Use and Swap Datasets

### A. Automatic Ingestion by Background Daemon
DTCM is configured with `DATA_SOURCE=dataset` in `.env` and `config.py`. The collector daemon automatically reads and streams records sequentially from `data/cpcb_indian_stations_telemetry.csv` without requiring any external internet API calls.

### B. Bulk Loading into Database
To populate or refresh the DTCM database with any dataset CSV file:
```bash
python scripts/load_dataset.py --file data/cpcb_indian_stations_telemetry.csv
```
To clear previous historical records before loading:
```bash
python scripts/load_dataset.py --file data/cpcb_indian_stations_telemetry.csv --clear
```

### C. Retraining Machine Learning Models
After loading a new or modified dataset:
```bash
python scripts/train_models.py
```
This trains the Linear Regression, Random Forest, and Decision Tree regressors directly against the dataset.

### D. Ingesting via Web Dashboard
You can also drag and drop any CSV dataset directly through the **Telemetry Data Ingestion** card in the dashboard UI at `http://localhost:5000/dashboard`.
