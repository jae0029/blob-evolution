# evo_sim/sim/lineage.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Iterable
from .models import Species, Creature

@dataclass
class SpeciesNode:
    species_id: int
    name: str
    color: Tuple[int, int, int]
    parent_id: Optional[int]
    birth_day: int
    extinct_day: Optional[int] = None
    current_count: int = 0

class LineageTracker:
    """
    Tracks species as nodes in a phylogenetic tree:
      - Nodes are Species (with parent->child relationships)
      - birth_day recorded on first appearance
      - extinct_day set when daily population hits zero
      - current_count updated each day
    """
    def __init__(self):
        self.nodes: Dict[int, SpeciesNode] = {}
        self.children: Dict[int, List[int]] = {}  # species_id -> child ids
        self._order: List[int] = []               # creation order for stable layout

    # ---- registration ----
    def register_root_species(self, species: Species, birth_day: int):
        if species.id in self.nodes:
            return
        self.nodes[species.id] = SpeciesNode(
            species_id=species.id,
            name=species.name,
            color=species.color,
            parent_id=None,
            birth_day=birth_day,
            extinct_day=None,
            current_count=0,
        )
        self.children[species.id] = []
        self._order.append(species.id)

    def register_speciation(self, parent: Species, child: Species, birth_day: int):
        # ensure parent exists
        if parent.id not in self.nodes:
            self.register_root_species(parent, birth_day)  # fallback
        # add child
        if child.id not in self.nodes:
            self.nodes[child.id] = SpeciesNode(
                species_id=child.id,
                name=child.name,
                color=child.color,
                parent_id=parent.id,
                birth_day=birth_day,
                extinct_day=None,
                current_count=0,
            )
            self.children.setdefault(parent.id, []).append(child.id)
            self.children.setdefault(child.id, [])
            self._order.append(child.id)

    # ---- daily updates ----
    def update_from_population(self, creatures: Iterable[Creature], day: int):
        # reset counts
        for node in self.nodes.values():
            node.current_count = 0

        for c in creatures:
            self.nodes[c.species.id].current_count += 1

        # mark extinctions if needed
        for sid, node in self.nodes.items():
            if node.extinct_day is None and node.birth_day <= day and node.current_count == 0:
                node.extinct_day = day

    # ---- layout helpers for rendering ----
    def roots(self) -> List[int]:
        return [sid for sid, n in self.nodes.items() if n.parent_id is None]

    def get_creation_order(self) -> List[int]:
        return list(self._order)

    def compute_layout_columns(self) -> Dict[int, int]:
        """
        Assign an x-column to each species to draw a tidy tree.
        Simple rule:
          - Traverse roots by creation order.
          - DFS over children (in creation order).
          - Assign columns incrementally.
        """
        order = self.get_creation_order()
        # build adjacency in creation order
        adj = {sid: list(self.children.get(sid, [])) for sid in self.nodes}
        for sid in adj:
            adj[sid].sort(key=lambda cid: order.index(cid) if cid in order else 10**9)

        columns: Dict[int, int] = {}
        col_counter = 0

        def dfs(sid: int):
            nonlocal col_counter
            columns[sid] = col_counter
            col_counter += 1
            for child in adj.get(sid, []):
                dfs(child)

        # do roots in creation order
        roots = [sid for sid in order if self.nodes[sid].parent_id is None]
        for r in roots:
            dfs(r)
        return columns

    # ---- accessors for renderer ----
    def segments(self, current_day: int) -> List[Tuple[int, int, int, int, Tuple[int,int,int]]]:
        """
        Returns vertical segments: (species_id, y0, y1, parent_id, color)
        y0 = birth_day, y1 = extinct_day or current_day
        """
        segs = []
        for sid, node in self.nodes.items():
            y0 = node.birth_day
            y1 = node.extinct_day if node.extinct_day is not None else current_day
            segs.append((sid, y0, y1, node.parent_id if node.parent_id is not None else -1, node.color))
        return segs

    def has_data(self) -> bool:
        return len(self.nodes) > 0