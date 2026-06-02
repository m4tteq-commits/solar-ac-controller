#!/usr/bin/env python3
"""
Solar AC Controller - Main Entry Point
Aplicație de automatizare AC bazată pe surplus solar

Rulează: python main.py
"""
import sys
import logging
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import settings
from modules.controller import SolarACController


def setup_logging():
    """Configure application logging."""
    log_path = PROJECT_ROOT / "logs"
    log_path.mkdir(exist_ok=True)

    logger = logging.getLogger("solar_ac")
    logger.setLevel(getattr(logging, settings.LOG_LEVEL, logging.INFO))

    # File handler
    fh = logging.FileHandler(
        settings.LOG_FILE, encoding="utf-8"
    )
    fh.setLevel(logging.INFO)

    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)

    logger.addHandler(fh)
    logger.addHandler(ch)

    # Also configure module loggers
    for mod_name in ['solarman', 'midea', 'decision', 'controller', 'email', 'telegram', 'web']:
        mod_logger = logging.getLogger(mod_name)
        mod_logger.setLevel(logging.INFO)
        mod_logger.addHandler(fh)
        mod_logger.addHandler(ch)

    return logger


def main():
    """Main application entry point."""
    logger = setup_logging()

    logger.info("=" * 60)
    logger.info("Solar AC Controller v1.0")
    logger.info("Automatizare AC bazată pe surplus solar")
    logger.info("=" * 60)
    logger.info(f"Setări: surplus>={settings.SURPLUS_THRESHOLD_KW}kW, "
                f"T°>={settings.TEMP_THRESHOLD}°C, "
                f"ore {settings.ALLOWED_HOURS_START}:00-{settings.ALLOWED_HOURS_END}:00")
    logger.info(f"Protecție compresor: min run {settings.MIN_RUN_TIME_MINUTES}min, "
                f"cooldown {settings.MIN_COOLDOWN_MINUTES}min")

    controller = SolarACController()

    try:
        controller.start()
    except KeyboardInterrupt:
        logger.info("Închidere prin Ctrl+C...")
    except Exception as e:
        logger.error(f"Eroare fatală: {e}", exc_info=True)
        sys.exit(1)
    finally:
        controller.stop()
        logger.info("Solar AC Controller - Oprire completă")


if __name__ == "__main__":
    main()
