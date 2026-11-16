import asyncio
import logging

from config.loader import load_config
from simulators.common import run_plant

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_plant(load_config(), 1))