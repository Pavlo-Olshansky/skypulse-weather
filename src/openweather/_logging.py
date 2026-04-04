from __future__ import annotations

import logging


class APIKeyRedactingFilter(logging.Filter):
    def __init__(self, api_key: str) -> None:
        super().__init__()
        self._api_key = api_key

    def filter(self, record: logging.LogRecord) -> bool:
        if self._api_key:
            record.msg = str(record.msg).replace(self._api_key, "***")
            if record.args:
                record.args = tuple(
                    str(a).replace(self._api_key, "***") if isinstance(a, str) else a
                    for a in record.args
                )
        return True


def get_logger(api_key: str | None = None) -> logging.Logger:
    logger = logging.getLogger("openweather")
    if api_key:
        logger.addFilter(APIKeyRedactingFilter(api_key))
    return logger
