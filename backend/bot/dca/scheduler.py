"""
Scheduler to execute DCA purchases periodically.
Uses APScheduler to schedule executions every 2 weeks.
"""

from datetime import datetime

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger

from shared.db.config import check_db_health

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

            # Health check DB before purchase
            is_healthy, msg = check_db_health()
            if not is_healthy:
                logger.error(f"❌ DB health check failed: {msg}")
                get_notifier().notify_error("Database Error", msg)
                return

            logger.info(f"✅ {msg}")
            success = self.dca_executor.run()

            if success:
                logger.info("✅ DCA job completed successfully")
            else:
                logger.error("❌ DCA job completed with errors")

        except Exception as e:
            logger.error(f"❌ Critical error in DCA job: {e}", exc_info=True)
            get_notifier().notify_crash(str(e))

    def _check_and_handle_misfires(self):
        """
        Check if there were any missed executions and handle them.
        This is called on startup to detect if the bot was down during a scheduled execution.
        Also logs the last purchase info for reference.
        """
        dca_config = self.config.dca
        now = datetime.now()

        # Log last purchase info
        last_purchase = self._get_last_purchase_info()
        if last_purchase:
            logger.info(f"📊 Last purchase: {last_purchase}")

        # Get the days this month we should have executed
        days = [int(d.strip()) for d in dca_config.days_of_month.split(",")]

        for day in days:
            # Check if this day has already passed this month
            if day < now.day:
                # Calculate the scheduled time for this day
                scheduled_time = now.replace(
                    day=day,
                    hour=dca_config.execution_hour,
                    minute=dca_config.execution_minute,
                    second=0,
                    microsecond=0,
                )

                # Check if it's within the grace period
                time_since_missed = now - scheduled_time
                grace_seconds = 86400 * dca_config.grace_period_days
                if time_since_missed.total_seconds() < grace_seconds:
                    # Check if a purchase was already made around this scheduled time
                    if self._was_purchase_made_around(scheduled_time):
                        logger.info(
                            f"✅ Purchase already made around {scheduled_time.strftime('%Y-%m-%d')} - no misfire"
                        )
                        continue

                    logger.warning(
                        f"⚠️ Detected missed execution from {scheduled_time.strftime('%Y-%m-%d %H:%M:%S')} "
                        f"({time_since_missed.days} days ago)"
                    )
                    get_notifier().notify_misfire(
                        scheduled_time.strftime("%Y-%m-%d %H:%M:%S"), will_retry=True
                    )
                    logger.info("▶️ Executing missed DCA purchase now...")
                    self._dca_job()
                    break  # Only execute once per startup

    def _get_last_purchase_info(self) -> str | None:
        """Get info about the last purchase for logging."""
        try:
            recent = self.dca_executor.tracker.get_recent_purchases(limit=1)
            if not recent:
                return None

            last = recent[0]
            timestamp_str = last.get("timestamp")
            if not timestamp_str:
                return None

            timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            if timestamp.tzinfo:
                timestamp = timestamp.replace(tzinfo=None)

            days_ago = (datetime.now() - timestamp).days
            return f"{timestamp.strftime('%Y-%m-%d %H:%M')} ({days_ago} days ago)"
        except Exception as e:
            logger.debug(f"Could not get last purchase info: {e}")
            return None

    def _was_purchase_made_around(self, scheduled_time: datetime) -> bool:
        """Check if a purchase was made within 1 day of the scheduled time."""
        try:
            recent = self.dca_executor.tracker.get_recent_purchases(limit=5)
            for purchase in recent:
                timestamp_str = purchase.get("timestamp")
                if not timestamp_str:
                    continue

                timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                if timestamp.tzinfo:
                    timestamp = timestamp.replace(tzinfo=None)

                # Check if purchase was within 1 day of scheduled time
                diff = abs((timestamp - scheduled_time).total_seconds())
                if diff < 86400:  # 1 day
                    return True
            return False
        except Exception:
            return False

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

        grace_seconds = 86400 * dca_config.grace_period_days
        self.scheduler.add_job(
            self._dca_job,
            trigger=trigger,
            id="dca_job",
            name="DCA Purchase Job",
            replace_existing=True,
            max_instances=1,  # Prevent concurrent executions
            misfire_grace_time=grace_seconds,
        )

        logger.info("✅ Scheduler configured successfully")
        logger.info(
            f"ℹ️  Misfire grace period: {dca_config.grace_period_days} days (missed executions will run on next startup)"
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

        # Check for missed executions (misfires)
        self._check_and_handle_misfires()

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
        except Exception as e:
            logger.error(f"💥 Scheduler crashed: {e}", exc_info=True)
            get_notifier().notify_crash(str(e))
            raise

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
