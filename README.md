# Wallet Service

A production-style Digital Wallet Microservice built with FastAPI, PostgreSQL, Kafka and Docker.

---

## Features

- Deposit Money
- Withdraw Money
- Check Wallet Balance
- Transaction History
- Idempotency Support
- Kafka Event Publishing
- PostgreSQL Database
- Docker Support
- Swagger API Documentation
- Unit Tests
- Integration Tests
- Contract Tests

---

## Tech Stack

- Python 3.12
- FastAPI
- SQLAlchemy
- PostgreSQL
- Kafka (Redpanda)
- Docker
- Pytest

---

## Project Structure

```
app/
    api/
    core/
    events/
    models/
    repositories/
    schemas/
    services/

tests/
    contract/
    integration/
    stress/
    unit/
```

---

## Installation

Clone the repository

```bash
git clone <repository-url>
cd wallet-service
```

Create Virtual Environment

```bash
python -m venv .venv
```

Activate

Mac/Linux

```bash
source .venv/bin/activate
```

Windows

```bash
.venv\Scripts\activate
```

Install dependencies

```bash
pip install -r requirements.txt
```

---

## Run PostgreSQL & Kafka

```bash
docker compose up -d
```

---

## Run API

```bash
uvicorn app.main:app --reload
```

Swagger

```
http://127.0.0.1:8000/docs
```

---

## Run Tests

Contract Tests

```bash
PYTHONPATH=. pytest tests/contract -v
```

Integration Tests

```bash
PYTHONPATH=. pytest tests/integration -v
```

Unit Tests

```bash
PYTHONPATH=. pytest tests/unit -v
```

Stress Tests

```bash
PYTHONPATH=. pytest tests/stress -v
```

---

## Kafka Topics

wallet.deposited

wallet.withdrawn

---

## API Endpoints

POST /wallet/deposit

POST /wallet/withdraw

GET /wallet/balance/{user_id}

GET /wallet/transactions/{user_id}

---

## Author

Suman Upreti

CyberBreach Internship 2026