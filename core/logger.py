import logging
import os
from datetime import datetime

def get_logger(name: str) -> logging.Logger:
    """
    Crée et retourne un logger configuré.
    Chaque module appellera cette fonction avec son propre nom.
    """
    logger = logging.getLogger(name)

    # Évite de dupliquer les handlers si get_logger() est appelé plusieurs fois
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    # Format : [2026-04-13 14:32:01] INFO     agent_poster.generator : Message
    formatter = logging.Formatter(
        fmt="[%(asctime)s] %(levelname)-8s %(name)s : %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Handler 1 : affiche dans le terminal
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    # Handler 2 : écrit dans un fichier logs/app.log
    os.makedirs("logs", exist_ok=True)
    file_handler = logging.FileHandler("logs/app.log", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger