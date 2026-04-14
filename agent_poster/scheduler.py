from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from dotenv import load_dotenv
from agent_poster.content_planner import ContentPlanner
from agent_poster.generator import PostGenerator
from agent_poster.publisher import LinkedInPublisher
from core.logger import get_logger

load_dotenv()
logger = get_logger("agent_poster.scheduler")


def run_daily_pipeline(dry_run: bool = False):
    """
    Pipeline complet du jour :
    1. Vérifie s'il y a un post prévu
    2. Choisit le sujet via ContentPlanner
    3. Génère le post via PostGenerator
    4. Publie via LinkedInPublisher
    """
    logger.info("="*40)
    logger.info("Démarrage du pipeline quotidien")

    try:
        # Étape 1 — plan du jour
        planner = ContentPlanner()
        params = planner.get_daily_post_params()

        if not params:
            logger.info("Pas de post prévu aujourd'hui — pipeline arrêté")
            return

        # Étape 2 — génération
        generator = PostGenerator()
        post = generator.generate(**params)
        logger.info(f"Post généré :\n{post}")

        # Étape 3 — publication
        publisher = LinkedInPublisher()
        succes = publisher.post(post, headless=True, dry_run=dry_run)

        if succes:
            logger.info("Pipeline quotidien terminé avec succès")
        else:
            logger.error("Échec de la publication")

    except Exception as e:
        logger.error(f"Erreur dans le pipeline : {e}")
        raise


class PostScheduler:
    """
    Planifie l'exécution automatique du pipeline quotidien.
    Lance le pipeline chaque matin à l'heure configurée.
    """

    def __init__(self, hour: int = 9, minute: int = 0, dry_run: bool = False):
        self.scheduler = BlockingScheduler(timezone="Europe/Paris")
        self.hour = hour
        self.minute = minute
        self.dry_run = dry_run
        logger.info(f"PostScheduler configuré — heure : {hour:02d}:{minute:02d}, dry_run={dry_run}")

    def start(self):
        """Démarre le scheduler — tourne indéfiniment jusqu'à Ctrl+C."""
        self.scheduler.add_job(
            func=run_daily_pipeline,
            trigger=CronTrigger(hour=self.hour, minute=self.minute),
            kwargs={"dry_run": self.dry_run},
            id="daily_post",
            name="Pipeline LinkedIn quotidien",
            replace_existing=True
        )

        logger.info(f"Scheduler démarré — prochain post à {self.hour:02d}:{self.minute:02d}")
        logger.info("Appuie sur Ctrl+C pour arrêter")

        try:
            self.scheduler.start()
        except KeyboardInterrupt:
            logger.info("Scheduler arrêté manuellement")
            self.scheduler.shutdown()