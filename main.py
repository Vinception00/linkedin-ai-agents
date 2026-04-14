from agent_poster.scheduler import run_daily_pipeline, PostScheduler
from dotenv import load_dotenv
from core.logger import get_logger

load_dotenv()
logger = get_logger("main")

# Test 1 — lance le pipeline une fois immédiatement en dry_run
logger.info("Test pipeline immédiat...")
run_daily_pipeline(dry_run=True)

# Test 2 — décommente pour lancer le vrai scheduler
# scheduler = PostScheduler(hour=9, minute=0, dry_run=True)
# scheduler.start()