import uuid
from abc import ABC, abstractmethod

from pydantic import BaseModel, Field


class Sandbox(ABC, BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))

    @abstractmethod
    def start(self):
        pass

    @abstractmethod
    def stop(self):
        pass
