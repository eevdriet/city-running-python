from abc import ABC, abstractmethod
from typing import Callable, Optional

import networkx as nx


class Command(ABC):
    def __init__(self, graph: nx.MultiDiGraph):
        self.graph = graph

    @abstractmethod
    def execute(self):
        pass

    @abstractmethod
    def undo(self):
        pass

    def redo(self):
        self.execute()


CommandFunc = Callable[..., Optional[Command]]
