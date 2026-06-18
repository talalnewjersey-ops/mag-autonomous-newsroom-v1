#!/usr/bin/env python3
"""
NEXUS-14: MoneyAbroadGuide Autonomous Newsroom V1
Main entry point for the 14-agent autonomous content production system.

Project Code Name: NEXUS-14
Repository: mag-autonomous-newsroom-v1
Target: MoneyAbroadGuide.com
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from orchestrator.orchestrator import Orchestrator

from config.config_loader import ConfigLoader
from monitoring.health_check import HealthChecker
from utils.logger import setup_logging


async def main():
    """Main entry point for NEXUS-14 Autonomous Newsroom."""
    # Setup logging
    setup_logging()
    logger = logging.getLogger("NEXUS-14")
    
    logger.info("=" * 60)
    logger.info("  NEXUS-14 — MoneyAbroadGuide Autonomous Newsroom V1")
    logger.info("  Starting 14-Agent Production System...")
    logger.info("=" * 60)
    
    # Load configuration
    config = ConfigLoader.load()
    logger.info(f"Configuration loaded: {config.environment} mode")
    
    # Health check
    health = HealthChecker(config)
    if not await health.check_all():
        logger.error("Health check failed. Aborting launch.")
        sys.exit(1)
    
    logger.info("All systems healthy. Launching production pipeline...")
    
    # Initialize orchestrator
    orchestrator = Orchestrator(config)
    
    
   
    
    # Run based on mode
    mode = config.get("run_mode", "scheduled")
    
    if mode == "scheduled":
        # Run the full scheduled production system
        logger.info("Running in SCHEDULED mode (06:00 / 09:30 / 16:30 / 18:30)")
        await orchestrator.run_full_pipeline()
    elif mode == "single":
        # Run a single production cycle
        logger.info("Running SINGLE production cycle...")
        await orchestrator.run_full_pipeline()
    elif mode == "batch1":
        # Run only morning batch
        logger.info("Running BATCH 1 (morning cycle)...")
        await orchestrator.run_batch(batch_id=1)
    elif mode == "batch2":
        # Run only evening batch
        logger.info("Running BATCH 2 (evening cycle)...")
        await orchestrator.run_batch(batch_id=2)
    else:
        logger.error(f"Unknown run mode: {mode}")
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.getLogger("NEXUS-14").info("System shutdown requested. Stopping gracefully...")
        sys.exit(0)
    except Exception as e:
        logging.getLogger("NEXUS-14").critical(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
