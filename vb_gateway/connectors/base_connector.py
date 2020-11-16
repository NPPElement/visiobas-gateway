from abc import ABC, abstractmethod


class Connector(ABC):

    @abstractmethod
    def open(self):
        pass

    @abstractmethod
    def close(self):
        pass

    @abstractmethod
    def __repr__(self):
        pass

    @abstractmethod
    def get_devices_objects(self, devices_id: list, obj_types: list):
        pass

    # @staticmethod
    # def get_file_logger(logger_name: str,
    #                     file_size_bytes: int,
    #                     file_path: Path = None,
    #                     log_format: str = None) -> Logger:
    #
    #     if file_path is None:
    #         base_path = Path(__file__).resolve().parent.parent.parent
    #         file_path = base_path / f'logs/{__name__}.log'
    #
    #     if log_format is None:
    #         log_format = '%(levelname)-8s [%(asctime)s] [%(threadName)s] %(name)s - (%(filename)s).%(funcName)s(%(lineno)d): %(message)s'
    #
    #     logger = getLogger(logger_name)
    #
    #     file_handler = RotatingFileHandler(filename=file_path,
    #                                        mode='a',
    #                                        maxBytes=file_size_bytes,
    #                                        backupCount=1,
    #                                        encoding='utf-8')
    #
    #     formatter = logging.Formatter(log_format)
    #     file_handler.setFormatter(formatter)
    #     logger.addHandler(file_handler)
    #
    #     return logger
