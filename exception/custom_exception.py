import sys
import traceback
from logger.custom_logger import CustomLogger

logger = CustomLogger().get_logger(__file__)

class DocumentPortalException(Exception):
    """Custom Exception handling for Document Portal"""
    def __init__(self, error_message: str, error_details: sys):
        _, _, error_tb = error_details.exc_info()
        self.filename = error_tb.tb_frame.f_code.co_filename
        self.fileno = error_tb.tb_lineno
        self.error_message = str(error_message)
        # *iterable → positional-arg unpacking; Expands an iterable into positional arguments (left-to-right).
        # **dict → keyword-arg unpacking. Expands a mapping (usually a dict) into keyword arguments.
        self.traceback_str = ''.join(traceback.format_exception(*error_details.exc_info()))

    def __str__(self):
        return f"""
        Error in [{self.filename}] at line [{self.fileno}]
        Message: [{self.error_message}]
        Traceback:
        {self.traceback_str}
        """
    

if __name__ == "__main__":
    try:
        # Simulate an error
        a = 1 / 0
        print(a)
    except Exception as e:
        app_exc = DocumentPortalException(e, sys)
        logger.error(app_exc)
        raise app_exc
