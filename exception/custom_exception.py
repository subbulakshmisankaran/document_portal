import traceback
from typing import Union
from logger.custom_logger import CustomLogger

logger = CustomLogger().get_logger(__name__)

class DocumentPortalException(Exception):
    """Custom Exception handling for Document Portal"""

    def __init__(self, error: Union[BaseException, str]):
        # Decide how to extract message and location/trace
        if isinstance(error, BaseException):
            tb = error.__traceback__
            if tb:
                last = traceback.extract_tb(tb)[-1]                  # original error site
                tb_str = ''.join(traceback.format_exception(type(error), error, tb))
            else:
                # Freshly constructed exception, no traceback yet -> use caller's frame
                stack = traceback.extract_stack(limit=3)
                last = stack[-2] if len(stack) >= 2 else None
                tb_str = ''.join(traceback.format_stack())
            msg = str(error)
        else:
            # Plain string message -> use caller's frame and current stack
            msg = str(error)
            stack = traceback.extract_stack(limit=3)
            last = stack[-2] if len(stack) >= 2 else None
            tb_str = ''.join(traceback.format_stack())

        # Populate fields
        self.filename = getattr(last, "filename", None)
        self.lineno   = getattr(last, "lineno", None)
        self.funcname = getattr(last, "name", None)
        self.error_message = msg
        self.traceback_str = tb_str

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
        logger.exception("%s", app_exc)            # pretty console + JSON file with traceback
        raise app_exc from e                        # keep clear causal chain
