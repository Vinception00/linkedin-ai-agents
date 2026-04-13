import os
from anthropic import Anthropic
from dotenv import load_dotenv
from core.logger import get_logger

load_dotenv()
logger = get_logger("core.claude_client")


class ClaudeClient:
    """
    Encapsule les appels à l'API Anthropic Claude.
    Tous les agents passent par cette classe.
    """

    def __init__(self):
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY manquante dans le fichier .env")
        self.client = Anthropic(api_key=api_key)
        self.model = "claude-opus-4-6"
        logger.info("ClaudeClient initialisé")

    def generate(self, system_prompt: str, user_prompt: str, max_tokens: int = 1000) -> str:
        """
        Envoie un prompt à Claude et retourne la réponse texte.
        
        Args:
            system_prompt: Le rôle et contexte donné à Claude
            user_prompt: La demande concrète
            max_tokens: Limite de longueur de la réponse
            
        Returns:
            La réponse de Claude sous forme de string
        """
        logger.debug(f"Appel Claude — modèle: {self.model}, max_tokens: {max_tokens}")

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                messages=[
                    {"role": "user", "content": user_prompt}
                ],
                system=system_prompt
            )
            result = response.content[0].text
            logger.debug(f"Réponse reçue ({len(result)} caractères)")
            return result

        except Exception as e:
            logger.error(f"Erreur appel Claude : {e}")
            raise