from __future__ import annotations

import asyncio
import unittest

from translator_server.capacity_limiter import (
    TranslationCapacityLimiter,
    TranslationQueueFullError,
    TranslationQueueTimeoutError,
)


class TranslationCapacityLimiterTests(unittest.IsolatedAsyncioTestCase):
    async def test_waits_for_active_slot_to_be_released(self) -> None:
        limiter = TranslationCapacityLimiter(
            max_concurrency=1,
            queue_size=1,
            queue_timeout_seconds=1,
        )

        async with limiter.slot():
            queued_slot = limiter.slot()
            waiter = asyncio.create_task(queued_slot.__aenter__())
            await asyncio.sleep(0)
            self.assertFalse(waiter.done())

        await waiter
        await queued_slot.__aexit__(None, None, None)

    async def test_rejects_when_queue_is_full(self) -> None:
        limiter = TranslationCapacityLimiter(
            max_concurrency=1,
            queue_size=1,
            queue_timeout_seconds=1,
        )

        async with limiter.slot():
            queued_slot = limiter.slot()
            waiter = asyncio.create_task(queued_slot.__aenter__())
            await asyncio.sleep(0)
            with self.assertRaises(TranslationQueueFullError):
                async with limiter.slot():
                    pass

        await waiter
        await queued_slot.__aexit__(None, None, None)

    async def test_times_out_while_waiting_for_slot(self) -> None:
        limiter = TranslationCapacityLimiter(
            max_concurrency=1,
            queue_size=1,
            queue_timeout_seconds=0.001,
        )

        async with limiter.slot():
            with self.assertRaises(TranslationQueueTimeoutError):
                async with limiter.slot():
                    pass

    def test_rejects_invalid_configuration(self) -> None:
        with self.assertRaisesRegex(ValueError, "max_concurrency"):
            TranslationCapacityLimiter(max_concurrency=0, queue_size=1, queue_timeout_seconds=1)
        with self.assertRaisesRegex(ValueError, "queue_size"):
            TranslationCapacityLimiter(max_concurrency=1, queue_size=-1, queue_timeout_seconds=1)
        with self.assertRaisesRegex(ValueError, "queue_timeout_seconds"):
            TranslationCapacityLimiter(max_concurrency=1, queue_size=1, queue_timeout_seconds=0)


if __name__ == "__main__":
    unittest.main()
