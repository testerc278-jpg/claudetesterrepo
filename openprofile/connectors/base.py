"""Common connector interface."""
from __future__ import annotations

from abc import ABC, abstractmethod

from ..config import Config
from ..http_client import PoliteClient


class SourceConnector(ABC):
    name: str = "base"

    def __init__(self, client: PoliteClient, config: Config):
        self.client = client
        self.cfg = config

    @abstractmethod
    def available(self) -> bool:
        """Whether this connector can run given current config (keys, etc.)."""
        raise NotImplementedError
