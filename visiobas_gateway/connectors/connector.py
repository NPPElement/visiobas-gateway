from abc import ABC, abstractmethod


class Connector(ABC):

    @abstractmethod
    def open(self):
        pass

    @abstractmethod
    def close(self):
        pass

    @abstractmethod
    def __str__(self):
        pass

    @abstractmethod
    def update_devices(self, devices: list):
        pass
