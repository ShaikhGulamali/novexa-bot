"""NOVEXA - Production Connected FastAPI Web Dashboard Server.

Seamlessly integrated with the Discord Bot process:
- Shares in-memory Discord gateway state and active guild caches
- Direct SQLite transaction execution via shared DatabaseManager
- Non-blocking uvicorn.Server runner running inside the bot's asyncio event loop
"""

import logging
import asyncio
from typing import Optional
import uvicorn
from config import DASHBOARD_PORT, DASHBOARD_HOST
from services.website.app import create_app

logger = logging.getLogger("novexa.dashboard")


class WebDashboard:
    """Production FastAPI Web Dashboard server for NOVEXA connected directly to the bot."""

    def __init__(self, bot, port: int = DASHBOARD_PORT, host: str = DASHBOARD_HOST):
        self.bot = bot
        self.port = port
        self.host = host
        self.app = create_app(bot)
        self.server: Optional[uvicorn.Server] = None
        self._server_task: Optional[asyncio.Task] = None

    async def start(self):
        """Start the uvicorn web server inside the bot's asyncio event loop."""
        if self.server is not None:
            return
        config = uvicorn.Config(
            app=self.app,
            host=self.host,
            port=self.port,
            log_level="warning",
            loop="asyncio",
            access_log=False,
        )
        self.server = uvicorn.Server(config)
        self._server_task = asyncio.create_task(self.server.serve())
        logger.info(f"Connected Web Dashboard & REST API listening at http://{self.host}:{self.port}")
        print(f"\n[NOVEXA] CONNECTED WEB DASHBOARD: http://localhost:{self.port}\n")

    async def stop(self):
        """Gracefully terminate the web server."""
        if self.server:
            self.server.should_exit = True
            if self._server_task:
                try:
                    await asyncio.wait_for(self._server_task, timeout=2.0)
                except (asyncio.TimeoutError, asyncio.CancelledError):
                    pass
            logger.info("Connected Web Dashboard stopped.")
