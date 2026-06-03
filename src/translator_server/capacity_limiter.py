from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncIterator


class TranslationQueueFullError(Exception):
    pass


class TranslationQueueTimeoutError(Exception):
    pass


class TranslationCapacityLimiter:
    def __init__(self, max_concurrency: int, queue_size: int, queue_timeout_seconds: float) -> None:
        if max_concurrency <= 0:
            raise ValueError("max_concurrency must be greater than 0")
        if queue_size < 0:
            raise ValueError("queue_size must be greater than or equal to 0")
        if queue_timeout_seconds <= 0:
            raise ValueError("queue_timeout_seconds must be greater than 0")

        self._max_concurrency = max_concurrency
        self._queue_size = queue_size
        self._queue_timeout_seconds = queue_timeout_seconds
        self._active = 0
        self._waiting = 0
        self._next_ticket = 0
        self._serving_ticket = 0
        self._cancelled_tickets: set[int] = set()
        self._condition = asyncio.Condition()

    @asynccontextmanager
    async def slot(self) -> AsyncIterator[None]:
        await self._acquire()
        try:
            yield
        finally:
            await self._release()

    async def _acquire(self) -> None:
        async with self._condition:
            if self._active < self._max_concurrency and self._waiting == 0:
                self._active += 1
                return

            if self._waiting >= self._queue_size:
                raise TranslationQueueFullError

            ticket = self._next_ticket
            self._next_ticket += 1
            self._waiting += 1
            acquired = False
            try:
                await asyncio.wait_for(
                    self._wait_for_turn(ticket),
                    timeout=self._queue_timeout_seconds,
                )
                self._serving_ticket += 1
                self._advance_serving_ticket()
                self._waiting -= 1
                self._active += 1
                acquired = True
                self._condition.notify_all()
            except TimeoutError as exc:
                raise TranslationQueueTimeoutError from exc
            finally:
                if not acquired:
                    self._waiting -= 1
                    self._cancelled_tickets.add(ticket)
                    self._advance_serving_ticket()
                    self._condition.notify_all()

    async def _wait_for_turn(self, ticket: int) -> None:
        while self._active >= self._max_concurrency or ticket != self._serving_ticket:
            await self._condition.wait()

    async def _release(self) -> None:
        async with self._condition:
            self._active -= 1
            self._condition.notify_all()

    def _advance_serving_ticket(self) -> None:
        while self._serving_ticket in self._cancelled_tickets:
            self._cancelled_tickets.remove(self._serving_ticket)
            self._serving_ticket += 1
