import threading
import uuid

from locust import HttpUser, between, events, task


# ============================================================
# WEEK 11 STRESS-TEST CONFIGURATION
# ============================================================

TARGET_OPERATIONS = 100_000
TENANT_COUNT = 1_000
LATENCY_BUDGET_MS = 200


# ============================================================
# GLOBAL METRICS
# ============================================================

_counter_lock = threading.Lock()

completed_operations = 0
over_budget_operations = 0

idempotency_replays = 0
idempotency_collisions = 0

_stop_requested = False
_locust_environment = None

_next_tenant_number = 1
assigned_tenants = set()


# ============================================================
# OPERATION COUNTER
# ============================================================

def _record_operation(response_time: float) -> bool:
    """
    Record one completed wallet HTTP operation.

    Returns True exactly once when TARGET_OPERATIONS has been
    reached and the Locust run should stop.
    """

    global completed_operations
    global over_budget_operations
    global _stop_requested

    should_stop = False

    with _counter_lock:
        completed_operations += 1

        if response_time > LATENCY_BUDGET_MS:
            over_budget_operations += 1

        if (
            completed_operations >= TARGET_OPERATIONS
            and not _stop_requested
        ):
            _stop_requested = True
            should_stop = True

    return should_stop


# ============================================================
# LOCUST TEST START
# ============================================================

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """
    Store the active Locust environment.

    This allows the request listener to stop the benchmark
    automatically when the 100,000-operation target is reached.
    """

    global _locust_environment

    _locust_environment = environment


# ============================================================
# REQUEST METRICS
# ============================================================

@events.request.add_listener
def on_request(
    request_type,
    name,
    response_time,
    response_length,
    response,
    context,
    exception,
    start_time,
    url,
    **kwargs,
):
    """
    Count completed Week 11 wallet operations and record
    requests exceeding the 200 ms latency budget.
    """

    tracked_operations = {
        "/wallet/deposit",
        "/wallet/withdraw",
        "/wallet/balance/{user_id}",
        "/wallet/deposit [idempotency-replay]",
        "/wallet/deposit [idempotency-collision]",
    }

    if name not in tracked_operations:
        return

    should_stop = _record_operation(
        response_time
    )

    if (
        should_stop
        and _locust_environment is not None
        and _locust_environment.runner is not None
    ):
        _locust_environment.runner.quit()


# ============================================================
# FINAL WEEK 11 REPORT
# ============================================================

@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """
    Print custom Week 11 measurements when the benchmark ends.
    """

    print()
    print("=" * 72)
    print("WEEK 11 WALLET STRESS TEST")
    print("=" * 72)

    print(
        f"Target operations: {TARGET_OPERATIONS}"
    )

    print(
        f"Completed operations: {completed_operations}"
    )

    print(
        f"Distinct tenants assigned: {len(assigned_tenants)}"
    )

    print(
        f"Operations > {LATENCY_BUDGET_MS} ms: "
        f"{over_budget_operations}"
    )

    if completed_operations > 0:
        over_budget_percentage = (
            over_budget_operations
            / completed_operations
            * 100
        )

        print(
            "Over-budget rate: "
            f"{over_budget_percentage:.4f}%"
        )

    print(
        f"Idempotency replays accepted: "
        f"{idempotency_replays}"
    )

    print(
        f"Idempotency collisions rejected: "
        f"{idempotency_collisions}"
    )

    if completed_operations >= TARGET_OPERATIONS:
        print(
            "Target status: REACHED"
        )
    else:
        print(
            "Target status: NOT REACHED"
        )

    print("=" * 72)
    print()


# ============================================================
# WALLET LOAD USER
# ============================================================

class WalletLoadUser(HttpUser):
    """
    Week 11 wallet stress-test user.

    The database has already been seeded with:

        load-tenant-1-user-1
        ...
        load-tenant-1000-user-1

    Each simulated Locust user is assigned one of the
    1,000 prepared wallet tenants.
    """

    wait_time = between(
        0.01,
        0.05,
    )

    def on_start(self):
        global _next_tenant_number

        with _counter_lock:
            tenant_number = _next_tenant_number

            _next_tenant_number += 1

            if _next_tenant_number > TENANT_COUNT:
                _next_tenant_number = 1

            assigned_tenants.add(tenant_number)

        self.user_id = (
            f"load-tenant-"
            f"{tenant_number}-user-1"
        )

    # ========================================================
    # NORMAL DEPOSIT
    # ========================================================

    @task(5)
    def deposit(self):
        """
        Normal wallet deposit using a unique idempotency key.
        """

        self.client.post(
            "/wallet/deposit",
            headers={
                "idempotency-key": str(
                    uuid.uuid4()
                ),
            },
            json={
                "user_id": self.user_id,
                "amount": 10,
                "currency": "USD",
            },
            name="/wallet/deposit",
        )

    # ========================================================
    # BALANCE CHECK
    # ========================================================

    @task(3)
    def balance_check(self):
        """
        Read the current wallet balance.
        """

        self.client.get(
            (
                f"/wallet/balance/"
                f"{self.user_id}"
                f"?currency=USD"
            ),
            name="/wallet/balance/{user_id}",
        )

    # ========================================================
    # NORMAL WITHDRAW
    # ========================================================

    @task(2)
    def withdraw(self):
        """
        Normal wallet withdrawal using a unique
        idempotency key.
        """

        self.client.post(
            "/wallet/withdraw",
            headers={
                "idempotency-key": str(
                    uuid.uuid4()
                ),
            },
            json={
                "user_id": self.user_id,
                "amount": 1,
                "currency": "USD",
            },
            name="/wallet/withdraw",
        )

    # ========================================================
    # IDEMPOTENCY REPLAY
    # ========================================================

    @task(1)
    def idempotency_replay(self):
        """
        Send the same deposit request twice using exactly
        the same idempotency key and payload.

        Expected behavior:

        First request:
            HTTP 200
            financial transaction is processed

        Second request:
            HTTP 200
            original result is returned
            no duplicate financial transaction is created
        """

        global idempotency_replays

        key = (
            "week11-replay-"
            f"{uuid.uuid4()}"
        )

        payload = {
            "user_id": self.user_id,
            "amount": 1,
            "currency": "USD",
        }

        first_response = self.client.post(
            "/wallet/deposit",
            headers={
                "idempotency-key": key,
            },
            json=payload,
            name=(
                "/wallet/deposit "
                "[idempotency-replay]"
            ),
        )

        if first_response.status_code != 200:
            return

        with self.client.post(
            "/wallet/deposit",
            headers={
                "idempotency-key": key,
            },
            json=payload,
            name=(
                "/wallet/deposit "
                "[idempotency-replay]"
            ),
            catch_response=True,
        ) as second_response:

            if second_response.status_code == 200:
                with _counter_lock:
                    idempotency_replays += 1

                second_response.success()

            else:
                second_response.failure(
                    "Expected HTTP 200 for identical "
                    "idempotency replay"
                )

    # ========================================================
    # IDEMPOTENCY COLLISION
    # ========================================================

    @task(1)
    def idempotency_collision(self):
        """
        Reuse the same idempotency key with a different
        request payload.

        Expected behavior:

        First request:
            HTTP 200

        Second request:
            HTTP 409

        HTTP 409 is the expected successful protection
        behavior for this benchmark.
        """

        global idempotency_collisions

        key = (
            "week11-collision-"
            f"{uuid.uuid4()}"
        )

        first_payload = {
            "user_id": self.user_id,
            "amount": 1,
            "currency": "USD",
        }

        conflicting_payload = {
            "user_id": self.user_id,
            "amount": 2,
            "currency": "USD",
        }

        first_response = self.client.post(
            "/wallet/deposit",
            headers={
                "idempotency-key": key,
            },
            json=first_payload,
            name=(
                "/wallet/deposit "
                "[idempotency-collision]"
            ),
        )

        if first_response.status_code != 200:
            return

        with self.client.post(
            "/wallet/deposit",
            headers={
                "idempotency-key": key,
            },
            json=conflicting_payload,
            name=(
                "/wallet/deposit "
                "[idempotency-collision]"
            ),
            catch_response=True,
        ) as second_response:

            if second_response.status_code == 409:
                with _counter_lock:
                    idempotency_collisions += 1

                # HTTP 409 is expected here.
                # Mark it successful from the load-test
                # perspective because the wallet correctly
                # prevented conflicting key reuse.
                second_response.success()

            else:
                second_response.failure(
                    "Expected HTTP 409 for conflicting "
                    "idempotency-key reuse"
                )