import os
from datetime import datetime
import logging

class CustomLogger:
    def __init__(self, logs_dir="logs"):

        # Create logs directory if doesnt exist
        self.logs_dir = os.path.join(os.getcwd(), logs_dir)
        os.makedirs(self.logs_dir, exist_ok=True)

        # Create timestamped log file name
        log_file_name = f"{datetime.now().strftime('%m_%d_%Y_%H_%M_%S')}.log"
        log_file_path = os.path.join(self.logs_dir, log_file_name)

        # Configure logging
        logging.basicConfig(
            filename=log_file_path,
            level=logging.INFO, # minimum level to be configured
            format="[ %(asctime)s ] %(levelname)s %(name)s (line:%(lineno)d) - %(message)s"
        )

    def get_logger(self, path=__file__):
        # Getting the file name from the file path and 
        # instantiate a logger object from Python's logging system.
        return logging.getLogger(os.path.basename(path))


if __name__=="__main__":
    obj =    CustomLogger()
    logger = obj.get_logger(__file__)
    logger.info("Custom logger module is initialized!")