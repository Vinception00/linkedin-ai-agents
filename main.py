from agent_poster.content_planner import ContentPlanner
from agent_poster.generator import PostGenerator
from core.logger import get_logger
from dotenv import load_dotenv

load_dotenv()
logger = get_logger("main")

planner = ContentPlanner()
params = planner.get_daily_post_params()

if params:
    logger.info(f"Post du jour : {params}")
    generator = PostGenerator()
    post = generator.generate(**params)
    print("\n" + "="*50)
    print(post)
    print("="*50)
else:
    logger.info("Pas de post prévu aujourd'hui")