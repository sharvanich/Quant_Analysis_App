# ⚡ Quant Analytics App

A **real-time quantitative analytics platform** that streams, processes, and visualizes live cryptocurrency market data.  
Built using **FastAPI**, **Redis**, **MySQL**, and **Streamlit**, this project showcases a scalable three-tier architecture with a background data worker for continuous ingestion and analytics computation.

---

## 🧠 Overview

The Quant Analytics App continuously collects tick data from Binance WebSocket, aggregates it into OHLCV candles, computes key statistical metrics (like Z-score, Spread, and Rolling Correlation), and visualizes them live in a Streamlit dashboard.

### 🎯 Core Features

- **Live Data Ingestion**: Streams raw tick data from Binance WebSocket.
- **Data Storage**: Persists tick and candlestick data in MySQL.
- **Analytics Engine**: Computes Hedge Ratio, Spread, Z-score, and Rolling Correlation.
- **Real-time Updates**: Uses Redis pub/sub to push live analytics instantly to clients.
- **Interactive Dashboard**: Streamlit frontend displays live charts and metrics.

---

## 🏗️ Architecture

```

quant-analytics-app/
├── backend/                        # FastAPI backend (Application Layer)
│   ├── main.py                     # Entry point (FastAPI app setup)
│   ├── config.py                   # Environment and configuration management
│   ├── database.py                 # SQLAlchemy DB connection and ORM
│   ├── schemas.py                  # Pydantic schemas for validation and response models
│   ├── models.py                   # SQLAlchemy models (TickData, OHLCV1m, AnalyticsCache)
│   ├── crud.py                     # Database query helpers
│   ├── core/
│   │   ├── analytics.py            # Analytics calculations (Z-score, Spread, Corr, etc.)
│   │   └── websocket_manager.py    # Active WebSocket client handler
│   └── api/
│       ├── historical_data.py      # REST endpoint for historical data
│       └── real_time.py            # WebSocket endpoint for live updates
│
├── data_worker/                    # Independent async data ingestion and analytics worker
│   ├── worker_main.py              # Orchestrates ingestion and analytics tasks
│   ├── ingestion_stream.py         # Connects to Binance WebSocket, stores raw ticks
│   ├── data_processing.py          # Resampling to 1m OHLCV candles
│   └── live_cacher.py              # Publishes live metrics to Redis
│
├── frontend/                       # Streamlit frontend (Presentation Layer)
│   ├── streamlit_app.py            # Dashboard UI and WebSocket listener
│   └── .streamlit/secrets.toml     # Backend API/WebSocket URLs and credentials
│
├── .env.example                    # Template for environment variables
├── docker-compose.yml              # Optional: easy setup for MySQL, Redis, FastAPI, Worker
├── requirements.txt                # Python dependencies
├── README.md                       # You are here
└── ws_test.py                      # Simple WebSocket client for testing backend

````

---

## ⚙️ Technologies Used

| Layer | Technology | Role |
|:------|:------------|:-----|
| Frontend | **Streamlit** | Real-time dashboard for live data visualization |
| Backend | **FastAPI** | Serves REST and WebSocket APIs |
| Worker | **Async Python (Pandas, asyncio)** | Data ingestion, resampling, analytics |
| Database | **MySQL** | Persistent data store |
| Cache | **Redis** | Live analytics cache & pub/sub messaging |
| Environment | **WSL / Docker Compose** | Local dev environment |

---

## 🚀 Setup and Running Locally

### 1️⃣ Clone the Repository
```bash
git clone https://github.com/sharvanich/quant-analytics-app.git
cd quant-analytics-app
````

### 2️⃣ Create Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3️⃣ Configure Environment Variables

Copy `.env.example` → `.env` and update:

```bash
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=yourpassword
MYSQL_DB=quant_data

REDIS_HOST=127.0.0.1
REDIS_PORT=6379
```

### 4️⃣ Start MySQL and Redis

You can run them manually or use Docker Compose:

```bash
docker-compose up -d
```

### 5️⃣ Initialize Database

Run the database models once:

```bash
python -m backend.models
python -m backend.create_tables
```

### 6️⃣ Run the Backend (FastAPI)

```bash
uvicorn backend.main:app --reload
```

Backend runs on → `http://127.0.0.1:8000`

### 7️⃣ Run the Data Worker

In a new terminal:

```bash
python -m data_worker.worker_main.py
```

### 8️⃣ Run the Frontend (Streamlit)

In another terminal:

```bash
cd frontend
streamlit run streamlit_app.py
```

Frontend runs on → `http://localhost:8501`

---

## 🧩 Testing WebSocket Connection

If you want to verify live updates manually:

```bash
python ws_test.py
```

Then publish dummy data in Redis:

```bash
redis-cli
PUBLISH live_updates:btcusdt '{"symbol":"btcusdt","price":64000,"zscore":0.5,"spread":1.2,"corr":0.95}'
```

## 🧠 Design Highlights

1. **Decoupled Architecture**:

   * Worker handles ingestion + analytics.
   * FastAPI handles API and WebSocket.
   * Streamlit focuses purely on visualization.

2. **Redis Pub/Sub**:

   * Enables instant message passing without polling.

3. **Asynchronous Processing**:

   * Uses `asyncio` and `aioredis` for non-blocking performance.

4. **Scalable Components**:

   * Each module (worker, API, frontend) can be containerized and scaled independently.

```
