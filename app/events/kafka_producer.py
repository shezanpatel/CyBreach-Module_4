import asyncio
import json
from concurrent.futures import Future

from aiokafka import AIOKafkaProducer

from app.core.config import settings


producer: AIOKafkaProducer | None = None
producer_loop: asyncio.AbstractEventLoop | None = None

KAFKA_PUBLISH_TIMEOUT_SECONDS = 5


async def start_producer():
    """
    Start the shared Kafka producer and remember the event loop that owns it.

    FastAPI starts this function from the application's lifespan event loop.
    The producer must continue to be used from that same loop.
    """
    global producer
    global producer_loop

    producer_loop = asyncio.get_running_loop()

    producer = AIOKafkaProducer(
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )

    await producer.start()


async def stop_producer():
    """
    Stop the shared Kafka producer on its owning event loop.
    """
    global producer
    global producer_loop

    if producer:
        await producer.stop()
        producer = None

    producer_loop = None


async def publish_event(
    topic: str,
    message: dict,
):
    """
    Publish an event using the shared application producer.

    This coroutine must execute on the event loop that owns the producer.
    """
    if producer is None:
        print(
            "⚠️ Kafka producer is not running; "
            f"skipping event: {topic}"
        )
        return

    try:
        await asyncio.wait_for(
            producer.send_and_wait(
                topic,
                message,
            ),
            timeout=KAFKA_PUBLISH_TIMEOUT_SECONDS,
        )

        print(
            f"📤 Event published to {topic}: {message}"
        )

    except asyncio.TimeoutError:
        print(
            f"⚠️ Kafka publish timed out after "
            f"{KAFKA_PUBLISH_TIMEOUT_SECONDS}s: {topic}"
        )

    except Exception as exc:
        print(
            f"⚠️ Kafka publish failed for {topic}: {exc}"
        )


def publish_event_sync(
    topic: str,
    message: dict,
) -> None:
    """
    Thread-safe bridge for synchronous wallet service functions.

    Wallet operations execute synchronously in FastAPI worker threads.
    The AIOKafkaProducer belongs to FastAPI's main asyncio event loop.

    asyncio.run() must not be used with that shared producer because it
    creates a different temporary event loop.

    Instead, schedule publish_event() on the producer's owning loop.
    """

    if producer is None or producer_loop is None:
        print(
            "⚠️ Kafka producer is not running; "
            f"skipping event: {topic}"
        )
        return

    if producer_loop.is_closed():
        print(
            "⚠️ Kafka producer event loop is closed; "
            f"skipping event: {topic}"
        )
        return

    future: Future = asyncio.run_coroutine_threadsafe(
        publish_event(
            topic,
            message,
        ),
        producer_loop,
    )

    try:
        future.result(
            timeout=KAFKA_PUBLISH_TIMEOUT_SECONDS + 1
        )
    except TimeoutError:
        future.cancel()
        print(
            "⚠️ Kafka synchronous publish bridge timed out: "
            f"{topic}"
        )
    except Exception as exc:
        print(
            "⚠️ Kafka synchronous publish bridge failed for "
            f"{topic}: {exc}"
        )