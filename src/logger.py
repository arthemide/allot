import logging.config


def setup_logging():  # pragma: no cover
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "standard": {
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                },
            },
            "handlers": {
                "console": {
                    "level": "DEBUG",
                    "class": "logging.StreamHandler",
                    "formatter": "standard",
                },
                "file": {
                    "level": "INFO",
                    "class": "logging.FileHandler",
                    "filename": "app.log",
                    "formatter": "standard",
                },
            },
            "loggers": {
                "": {  # root logger
                    "handlers": ["console", "file"],
                    "level": "INFO",
                    "propagate": True,
                },
                "my_module": {
                    "handlers": ["console"],
                    "level": "INFO",
                    "propagate": False,
                },
            },
        }
    )
