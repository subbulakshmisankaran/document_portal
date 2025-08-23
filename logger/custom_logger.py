import os
from datetime import datetime, timezone
import logging
import structlog



class CustomLogger:
    """
    A structured JSON logger for the 'Document Portal' project.

      - Sends logs to BOTH console and file (JSON lines).
      - Uses structlog so logs are structured (key/value), easy to parse & search.
      - call CustomLogger().get_logger(__name__).
    """
    # Class level gaurd to avoid configuring logger multiple times in multi-import scenarios
    _configured: bool = False

    def __init__(self, logs_dir: str = "logs",
                 level: int = logging.INFO) -> None:

        # Ensure ./logs directory exists
        self.logs_dir = os.path.join(os.getcwd(), logs_dir)
        os.makedirs(self.logs_dir, exist_ok=True)

        # Create timestamped log file name
        log_file_name = datetime.now(timezone.utc).strftime('%m_%d_%Y_%H_%M_%S') + ".log"
        self.log_file_path = os.path.join(self.logs_dir, log_file_name)

        self.level = level

        if not CustomLogger._configured:
            self._configure_stdlib_and_structlog()
            CustomLogger._configured = True


    def _configure_stdlib_and_structlog(self) -> None:
        # Common enrichers before rendering (applied for both console and file)
        pre_chain = [
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,                          # -> stringified traceback
            structlog.processors.TimeStamper(fmt="iso", key="timestamp", utc=True),
            structlog.processors.EventRenamer(to="event"),
            structlog.processors.CallsiteParameterAdder(parameters=(
                structlog.processors.CallsiteParameter.FILENAME,
                structlog.processors.CallsiteParameter.FUNC_NAME,
                structlog.processors.CallsiteParameter.LINENO,
                structlog.processors.CallsiteParameter.MODULE,
            )),
        ]

        # Console: pretty/human friendly
        console = logging.StreamHandler()
        console.setLevel(self.level)
        console.setFormatter(
            structlog.stdlib.ProcessorFormatter(
                processor=structlog.dev.ConsoleRenderer(sort_keys=False),
                foreign_pre_chain=pre_chain,
            )
        )

        # File: strict JSON, one record per line
        file_handler = logging.FileHandler(self.log_file_path, encoding="utf-8")
        file_handler.setLevel(self.level)
        file_handler.setFormatter(
            structlog.stdlib.ProcessorFormatter(
                processor=structlog.processors.JSONRenderer(),
                foreign_pre_chain=pre_chain,
            )
        )

        # Root logger wiring
        root = logging.getLogger()
        root.setLevel(self.level)
        # avoid duplicate handlers across re-imports
        for h in list(root.handlers):
            root.removeHandler(h)
        root.addHandler(console)
        root.addHandler(file_handler)

        # Defer final rendering to handler formatters
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.TimeStamper(fmt="iso", key="timestamp", utc=True),
                structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
            ],
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )

    def get_logger(self, path=__file__):
        # Getting the file name from the file path
        logger_name =  os.path.basename(path)
        return structlog.get_logger(logger_name)



# # --- Usage Example ---
if __name__ == "__main__":
     logger = CustomLogger().get_logger(__file__)
     logger.info("User uploaded a file", user_id=123, filename="report.pdf")
     logger.error("Failed to process PDF", error="File not found", user_id=123)