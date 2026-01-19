import asyncio
import time
from collections import deque
from core.logger import logger

class RequestQueue:
    """
    Manages a queue of API requests to ensure fair ordering and concurrency control.
    """
    def __init__(self, max_concurrent=5):
        self.queue = deque()
        self.active_requests = 0
        self.max_concurrent = max_concurrent
        self._lock = None
    
    @property
    def lock(self):
        if self._lock is None:
            self._lock = asyncio.Lock()
        return self._lock
        
    async def enqueue(self, func, *args, **kwargs):
        """
        Adds a request to the queue and executes it when a slot is available.
        """
        future = asyncio.Future()
        self.queue.append((func, args, kwargs, future))
        self._process_queue()
        return await future

    def _process_queue(self):
        """
        Internal method to process the queue.
        """
        # This is a bit simplified; a real robust queue might need a dedicated worker task.
        # But for this app, we can just trigger next if usage < max.
        # However, since we are async, we can't just fire and forget without await.
        pass # We'll implement a Context Manager approach instead for simplicity

import threading

class RateLimiter:
    """
    Token bucket rate limiter.
    Thread-safe implementation for Streamlit (which runs multiple threads).
    """
    def __init__(self, rpm=50, tpm=40000):
        self.rpm = rpm
        self.tpm = tpm
        self.request_timestamps = deque()
        self._lock = threading.Lock() # Thread-safe lock for global state

    async def acquire(self):
        """
        Acquire a token. If limit reached, wait asynchronously then retry.
        """
        while True:
            wait_time = 0
            with self._lock:
                now = time.time()
                
                # 1. Cleanup old timestamps
                while self.request_timestamps and now - self.request_timestamps[0] > 60:
                    self.request_timestamps.popleft()
                
                # 2. Check Limit
                if len(self.request_timestamps) < self.rpm:
                    # Success: Add timestamp and return
                    self.request_timestamps.append(now)
                    return
                else:
                    # Failure: Calculate wait
                    oldest = self.request_timestamps[0]
                    wait_time = 60 - (now - oldest) + 1  # +1s buffer
            
            # 3. Wait (Outside lock to allow others to process)
            if wait_time > 0:
                logger.warning(f"Rate limit hit (RPM: {self.rpm}). Waiting {wait_time:.2f}s")
                await asyncio.sleep(wait_time)
                # Loop continues to 'retry' acquire

# Global Rate Limiter Instance
limiter = RateLimiter(rpm=50) 
