"""
Scheduler to execute DCA purchases periodically.
Uses APScheduler to schedule executions every 2 weeks.
"""

from datetime import datetime

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger

from .config import Config
from .dca_executor import create_dca_executor
from .email_notifier import get_notifier


class DCAScheduler:
    """
    Scheduler to execute the DCA bot automatically and periodically.
    """

    def __init__(self, config: Config):
        """
        Initialize the scheduler.

        Args:
            config: Bot configuration
        """
        self.config = config
        self.scheduler = BlockingScheduler()
        self.dca_executor = create_dca_executor(config)

    def _dca_job(self):
        """
        Job executed by the scheduler to launch a DCA purchase.
        """
        try:
            logger.info("🔔 DCA scheduled job triggered")
            success = self.dca_executor.run()

            if success:
                logger.info("✅ DCA job completed successfully")
            else:
                logger.error("❌ DCA job completed with errors")

        except Exception as e:
            logger.error(f"❌ Critical error in DCA job: {e}", exc_info=True)

    def setup_schedule(self):
        """
        Configure the DCA execution schedule according to the configuration.
        Uses CronTrigger for reliable scheduling on specific days of the month.
        """
        dca_config = self.config.dca

        # Priority 1: Use days_of_month if specified (most reliable)
        if dca_config.days_of_month:
            trigger = CronTrigger(
                day=dca_config.days_of_month,
                hour=dca_config.execution_hour,
                minute=dca_config.execution_minute,
            )
            logger.info(
                f"📅 Schedule: Days {dca_config.days_of_month} of each month "
                f"at {dca_config.execution_hour:02d}:{dca_config.execution_minute:02d}"
            )
        else:
            logger.error(
                "❌ No valid scheduling configuration found (DCA_DAYS_OF_MONTH is required)"
            )
            raise ValueError("DCA_DAYS_OF_MONTH must be specified for scheduling")

        self.scheduler.add_job(
            self._dca_job,
            trigger=trigger,
            id="dca_job",
            name="DCA Purchase Job",
            replace_existing=True,
            max_instances=1,  # Prevent concurrent executions
            misfire_grace_time=86400
            * 7,  # Allow 7 days grace period for missed executions
        )

        logger.info("✅ Scheduler configured successfully")
        logger.info(
            "ℹ️  Misfire grace period: 7 days (missed executions will run on next startup within 7 days)"
        )

    def start(self, run_immediately: bool = False):
        """
        Start the scheduler.

        Args:
            run_immediately: If True, execute a purchase immediately on startup
        """
        logger.info("🚀 Starting DCA scheduler...")
        logger.info(f"Configuration: {self.config}")

        # Configure the schedule
        self.setup_schedule()

        # Execute immediately if requested
        if run_immediately:
            logger.info("▶️ Immediate execution requested")
            self._dca_job()

        # Display next executions
        next_run_str = None
        try:
            job = self.scheduler.get_job("dca_job")
            if job and job.trigger:
                next_run = job.trigger.get_next_fire_time(None, datetime.now())
                if next_run:
                    next_run_str = next_run.strftime("%Y-%m-%d %H:%M:%S")
                    logger.info(f"⏰ Next scheduled execution: {next_run_str}")
        except Exception as e:
            logger.warning(f"Could not determine next run time: {e}")

        # Send startup notification
        get_notifier().notify_startup(next_run_str)

        # Start the scheduler (blocking)
        try:
            logger.info("✅ Scheduler started. Waiting for next executions...")
            self.scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            logger.info("🛑 Scheduler stop requested")
            self.shutdown()

    def shutdown(self):
        """
        Gracefully stop the scheduler.
        """
        logger.info("🛑 Stopping scheduler...")
        self.scheduler.shutdown(wait=True)
        logger.info("✅ Scheduler stopped")

    def run_once(self):
        """
        Execute DCA once (manual mode).
        """
        logger.info("▶️ Manual DCA execution (once)")
        self._dca_job()
