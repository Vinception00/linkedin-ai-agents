from core.logger import get_logger
from core.claude_client import ClaudeClient

logger = get_logger("main")
logger.info("Projet linkedin-ai-agents démarré")

# Test ClaudeClient
client = ClaudeClient()
reponse = client.generate(
    system_prompt="Tu es un assistant spécialisé en data science.",
    user_prompt="Donne-moi un conseil en une phrase pour un data scientist junior."
)
logger.info(f"Réponse Claude : {reponse}")