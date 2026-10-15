# Integration Runbook

## Start

```powershell
Copy-Item .env.example .env
docker compose up -d redis redpanda redpanda-init postgres
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt psycopg2-binary
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Full Docker stack:

```powershell
docker compose up --build
```

## Verify Health

```powershell
curl http://127.0.0.1:8000/api/v1/integration/health
```

## Verify Score Display Flow

Produce:

```powershell
docker compose exec redpanda rpk topic produce mod3.score --brokers redpanda:9092
```

Message:

```json
{"event_type":"mod3.score","event_id":"score-1","tenant_id":"tenant-a","timestamp":"2026-09-20T00:00:00Z","data":{"score":82.5,"previous_score":80.0,"trend":"up","components":{"training":40,"response":42.5}}}
```

Check Redis and published event:

```powershell
docker compose exec redis redis-cli GET score:tenant-a
docker compose exec redpanda rpk topic consume score.displayed --brokers redpanda:9092 --num 1
```

## Verify Notification Flow

Produce:

```powershell
docker compose exec redpanda rpk topic produce achievement.awarded --brokers redpanda:9092
```

Message:

```json
{"event_type":"achievement.awarded","event_id":"ach-1","tenant_id":"tenant-a","timestamp":"2026-09-20T00:00:00Z","data":{"achievement_id":"first-defense","achievement_name":"First Defense","user_id":1,"points":50}}
```

Check Notification Hub and published event:

```powershell
curl "http://127.0.0.1:8000/api/v1/notifications/?user_id=1"
docker compose exec redpanda rpk topic consume notification.sent --brokers redpanda:9092 --num 1
```

## Verify Analytics Flow

Produce:

```powershell
docker compose exec redpanda rpk topic produce wallet.transaction --brokers redpanda:9092
```

Message:

```json
{"event_type":"wallet.transaction","event_id":"wallet-1","tenant_id":"tenant-a","timestamp":"2026-09-20T00:00:00Z","data":{"transaction_id":"txn-1","amount":10.0,"currency":"USD","direction":"credit","status":"completed","user_id":1}}
```

Check Analytics Engine and published event:

```powershell
curl "http://127.0.0.1:8000/api/v1/analytics?tenant_id=tenant-a"
docker compose exec redpanda rpk topic consume analytics.report --brokers redpanda:9092 --num 1
```

## Tests

```powershell
pytest tests/integration/test_app_integration_layer.py
```
