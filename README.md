# Open Source Data Warehouse Pipeline
### Technical Validation of Data Warehouse Architecture for RCI's Intranet
**Using Apache NiFi · ClickHouse · Apache Superset · Python · Docker**

---

## Overview

This project builds a **scalable, reliable, and flexible open-source data warehouse pipeline** capable of ingesting data from heterogeneous sources (such as MySQL), applying complex transformation logic in Python, storing analytical results in ClickHouse, and surfacing insights through interactive Apache Superset dashboards — all containerised with Docker.

The **Delay Accountability Analysis System** is included as the primary test case, demonstrating the pipeline's end-to-end capability on a real-world committee-based demand approval workflow. This test case was developed and validated during an internship at **Research Centre Imarat (RCI), DRDO, Hyderabad**.

---

## Technology Stack

| Component       | Technology       | Version | Role                                         |
|-----------------|------------------|---------|----------------------------------------------|
| Data Source     | MySQL            | 9.7.0   | Source OLTP database                         |
| Data Ingestion  | Apache NiFi      | 2.3.0   | Incremental extraction, routing, merging     |
| Transformation  | Python 3         | 3.10+   | Business logic, delay attribution algorithm  |
| Data Warehouse  | ClickHouse       | 24.3    | Columnar analytical storage                  |
| Visualisation   | Apache Superset  | Latest  | Interactive dashboards and filters           |
| Deployment      | Docker           | Latest  | Containerised multi-service deployment       |

---

## Project Structure

```
.
├── docker-compose.yml          # Full stack deployment
├── Dockerfile.superset         # Custom Superset image with ClickHouse driver
├── scripts/
│   └── transform.py            # Python transformation script (NiFi ExecuteStreamCommand)
├── clickhouse/
│   └── schema.sql              # ClickHouse warehouse schema (tables + views)
├── mysql/
│   └── schema.sql              # MySQL source database schema
├── nifi/
│   └── NiFi_Flow_all_p.json    # Exported NiFi pipeline flow
└── superset/
    └── dashboard_export.zip    # Exported Superset dashboard
```

---

## Pipeline Architecture

```
MySQL
  └─► QueryDatabaseTable (×4)
        └─► UpdateAttribute
              └─► ConvertRecord
                    └─► MergeContent  ← waits for all 4 tables (Min=Max=4, Bin Age=2 min)
                          └─► ExecuteStreamCommand (Python transform.py)
                                └─► SplitText
                                      └─► RouteOnContent
                                            ├─► PutDatabaseRecord → demand_delays
                                            └─► PutDatabaseRecord → member_delays
                                                    └─► Apache Superset Dashboard
```

---

## Quick Start

### Prerequisites
- Docker Desktop installed and running
- Git installed
- At least 8 GB RAM allocated to Docker

### 1. Clone the repository
```bash
git clone https://github.com/YOUR_USERNAME/open-source-data-warehouse.git
cd open-source-data-warehouse
```

### 2. Configure credentials
Open `docker-compose.yml` and replace the placeholder passwords with your own:
```yaml
CLICKHOUSE_PASSWORD: "your_password_here"
SINGLE_USER_CREDENTIALS_PASSWORD: "your_nifi_password_here"
```

### 3. Start the stack
```bash
docker compose up -d
```

This starts three containers:
| Service     | URL                        | Default Login        |
|-------------|----------------------------|----------------------|
| Apache NiFi | https://localhost:8443/nifi | admin / (set above)  |
| ClickHouse  | http://localhost:8123       | admin / (set above)  |
| Superset    | http://localhost:8089       | admin / admin        |

### 4. Set up MySQL source database
Run the MySQL schema:
```sql
source mysql/schema.sql
```

### 5. Set up ClickHouse warehouse
Connect to ClickHouse and run:
```sql
source clickhouse/schema.sql
```

### 6. Load the NiFi flow
- Open NiFi at `https://localhost:8443/nifi`
- Upload `nifi/NiFi_Flow_all_p.json` via the NiFi canvas

### 7. Import the Superset dashboard
- Open Superset at `http://localhost:8089`
- Go to **Dashboards → Import**
- Upload `superset/dashboard_export.zip`

---

## Test Case: Delay Accountability Analysis

The pipeline is validated using a committee-based demand approval workflow. The system computes:

| Metric | Description |
|--------|-------------|
| `T_total` | Total demand processing time (end_date − initialization_date) |
| `T_user` | User-owned delay (union of all query-response intervals) |
| `T_committee` | Committee-owned delay (T_total − T_user) |
| `T_member` | Per-member idle accountability (four-case algorithm) |
| `delay_flag` | 1 = user responsible, 0 = committee responsible |
| `passive_flag` | 1 = member raised no query and gave no recommendation |
| `accountability_rank` | Rank 1 = most accountable member on this demand |

### Four-Case Member Accountability Algorithm

| Case | Has Queries | Has Recommendation | Result |
|------|-------------|-------------------|--------|
| 1 | No | No | Passive — T_member = 0 |
| 2 | Yes | No | Idle periods between queries only |
| 3 | No | Yes | T_member = rec_date − T_start |
| 4 | Yes | Yes | Idle periods + post-last-query period |

---

## Dashboard

The **Demand Delay Accountability Dashboard** in Superset contains 9 charts:

1. Total Demands Processed *(Big Number)*
2. Delay Ownership — User vs Committee *(Pie Chart)*
3. User vs Committee Delay Days by Demand *(Bar Chart)*
4. User-Delay Proportion Trend Monthly *(Line Chart)*
5. Member Accountability Ranking *(Table)*
6. User vs Committee Delay Trend Monthly *(Area Chart)*
7. Passive Members Count *(Bar Chart)*
8. Role vs Accountability Rank Distribution *(Pivot Table)*
9. Member Delay Heatmap by Demand *(Heatmap)*

---

## Key Configuration Notes

**MergeContent processor** must be configured with:
- Minimum Number of Entries: `4`
- Maximum Number of Entries: `4`
- Max Bin Age: `2 min`

This ensures all four MySQL tables arrive together before the Python script is invoked.

**ClickHouse deduplication** uses `ReplacingMergeTree()` on both tables. All Superset datasets point to the `_view` versions (with `FINAL`) to guarantee deduplicated reads.

---

## Authors

**Sadaram Bhanuja Sripadini · Dheeraj D · Korada Chandana Priya · Sravani Reddy**  
B.Tech (CSE) — GITAM University, Visakhapatnam

Internship at **Research Centre Imarat (RCI), DRDO, Hyderabad**  
Under the guidance of **Raj Dev Gangwar, Scientist-B**  
Certified by **Dr. Santanu Chatterjee, Scientist-F**, Directorate of IT  
*May – June 2026*

---

## License

This project is open-source and intended for educational and research purposes.
