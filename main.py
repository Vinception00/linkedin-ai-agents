from core.logger import get_logger
from agent_poster.generator import PostGenerator

logger = get_logger("main")
logger.info("Test PostGenerator")

generator = PostGenerator()

post = generator.generate(
    post_type="conseil",
    sujet="nettoyer un dataset avec pandas",
    contexte="j'ai passé des heures à débugger avant de comprendre l'importance du preprocessing"
)

print("\n" + "="*50)
print(post)
print("="*50)