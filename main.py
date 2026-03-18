"""CLI entry point for the loan underwriting pipeline."""
import asyncio
import logging
import os
import sys

from dotenv import load_dotenv

from pipeline import run_pipeline

load_dotenv()

DOCS_FOLDER = "data/documents"
REPORTS_FOLDER = "data/reports"

os.makedirs(REPORTS_FOLDER, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(os.path.join(REPORTS_FOLDER, "pipeline.log")),
    ],
)

if __name__ == "__main__":
    asyncio.run(run_pipeline(DOCS_FOLDER, REPORTS_FOLDER))
