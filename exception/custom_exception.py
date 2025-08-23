import traceback
from logger.custom_logger import CustomLogger

logger = CustomLogger().get_logger(__name__)

class DocumentPortalException(Exception):
    """Custom Exception handling for Document Portal"""
    def __init__(self, error: BaseException):
        tb = error.__traceback__
        last = traceback.extract_tb(tb)[-1] if tb else None

        self.filename = last.filename if last else None
        self.lineno   = last.lineno   if last else None
        self.funcname = last.name     if last else None
        self.error_message = str(error)

        # Keep a formatted traceback for structured/JSON logging if desired
        self.traceback_str = ''.join(
            traceback.format_exception(type(error), error, error.__traceback__)
        )

        super().__init__(self.error_message)

    def __str__(self):
        loc = f"{self.filename}:{self.lineno}" if self.filename and self.lineno else "unknown"
        return f"{self.__class__.__name__}({self.error_message}) at {loc}"

if __name__ == "__main__":
    try:
        # Simulate an error
        a = 1 / 0
        print(a)
    except Exception as e:
        app_exc = DocumentPortalException(e)
        logger.exception("%s", app_exc)
        raise app_exc from e
