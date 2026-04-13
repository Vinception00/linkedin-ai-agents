from agent_poster.generator import PostGenerator
from agent_poster.publisher import LinkedInPublisher
from core.logger import get_logger
from dotenv import load_dotenv

load_dotenv()
logger = get_logger("main")

generator = PostGenerator()
post = generator.generate(
    post_type="conseil",
    sujet="nettoyer un dataset avec pandas",
    contexte="j'ai passé des heures à débugger avant de comprendre l'importance du preprocessing"
)

print("\n" + "="*50)
print(post)
print("="*50 + "\n")

publisher = LinkedInPublisher()
succes = publisher.post(post, headless=False, dry_run=True)

if succes:
    logger.info("Pipeline complet : post généré et publié")
else:
    logger.error("Échec de la publication")