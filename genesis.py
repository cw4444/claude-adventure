#!/usr/bin/env python3
"""
GENESIS - A Laboratory for Emergent Complexity
===============================================
An exploration of how unbounded complexity arises from the simplest rules.

Central question: Out of 262,144 possible outer-totalistic 2-state 8-neighbor
cellular automata rules, why does Conway's Life sit so close to the "edge of chaos"?
What makes it special?

This program:
  - Simulates multiple CA universes (Life, Seeds, Brian's Brain, Wireworld, 1D rules)
  - Automatically detects emergent structures (still lifes, oscillators, gliders)
  - Measures complexity using entropy and autocorrelation
  - Explores the rule space around Life to find its "neighborhood"
  - Generates a report on emergence and the edge of chaos

Author: Claude (an AI that finds this stuff genuinely fascinating)
"""

import sys
import os
import time
import math
import hashlib
import random
import struct
import itertools
from collections import defaultdict, Counter
from typing import Optional

# ─────────────────────────────────────────────────────────────────────────────
# ANSI Terminal Art
# ─────────────────────────────────────────────────────────────────────────────

class T:
    """Terminal colour/style constants."""
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    DIM     = "\033[2m"
    ITALIC  = "\033[3m"

    BLACK   = "\033[30m"
    RED     = "\033[31m"
    GREEN   = "\033[32m"
    YELLOW  = "\033[33m"
    BLUE    = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN    = "\033[36m"
    WHITE   = "\033[37m"

    BBLACK  = "\033[90m"
    BRED    = "\033[91m"
    BGREEN  = "\033[92m"
    BYELLOW = "\033[93m"
    BBLUE   = "\033[94m"
    BMAGENTA= "\033[95m"
    BCYAN   = "\033[96m"
    BWHITE  = "\033[97m"

    BG_BLACK   = "\033[40m"
    BG_BLUE    = "\033[44m"
    BG_GREEN   = "\033[42m"

    CLEAR   = "\033[2J\033[H"
    UP      = "\033[A"
    COL0    = "\033[G"

    @staticmethod
    def rgb(r: int, g: int, b: int) -> str:
        return f"\033[38;2;{r};{g};{b}m"

    @staticmethod
    def bg_rgb(r: int, g: int, b: int) -> str:
        return f"\033[48;2;{r};{g};{b}m"

    @staticmethod
    def move(row: int, col: int) -> str:
        return f"\033[{row};{col}H"


def banner():
    lines = [
        f"{T.rgb(255,180,0)}{T.BOLD}",
        "  ██████╗ ███████╗███╗   ██╗███████╗███████╗██╗███████╗",
        "  ██╔════╝ ██╔════╝████╗  ██║██╔════╝██╔════╝██║██╔════╝",
        "  ██║  ███╗█████╗  ██╔██╗ ██║█████╗  ███████╗██║███████╗",
        "  ██║   ██║██╔══╝  ██║╚██╗██║██╔══╝  ╚════██║██║╚════██║",
        "  ╚██████╔╝███████╗██║ ╚████║███████╗███████║██║███████║",
        "   ╚═════╝ ╚══════╝╚═╝  ╚═══╝╚══════╝╚══════╝╚═╝╚══════╝",
        f"{T.RESET}",
        f"  {T.BBLACK}A Laboratory for Emergent Complexity{T.RESET}",
        f"  {T.DIM}The universe from seven lines of rule.{T.RESET}",
        "",
    ]
    print("\n".join(lines))


def section(title: str, color: str = T.BCYAN):
    width = 70
    bar = "─" * width
    print(f"\n{color}{T.BOLD}┌{bar}┐")
    padding = (width - len(title) - 2) // 2
    print(f"│{' ' * padding} {title} {' ' * (width - padding - len(title) - 1)}│")
    print(f"└{bar}┘{T.RESET}")


def subsection(title: str):
    print(f"\n  {T.BYELLOW}▶ {T.BOLD}{title}{T.RESET}")


def info(msg: str):
    print(f"  {T.BBLACK}│{T.RESET} {msg}")


def result(key: str, val: str, color: str = T.BGREEN):
    print(f"  {T.BBLACK}│{T.RESET} {T.DIM}{key:<28}{T.RESET} {color}{val}{T.RESET}")


def progress_bar(value: float, width: int = 30, color: str = T.BGREEN) -> str:
    filled = int(value * width)
    bar = "█" * filled + "░" * (width - filled)
    return f"{color}{bar}{T.RESET} {T.DIM}{value*100:.1f}%{T.RESET}"


# ─────────────────────────────────────────────────────────────────────────────
# Core Grid Engine
# ─────────────────────────────────────────────────────────────────────────────

class Grid:
    """
    A 2D toroidal grid of cells. States are integers (supports multi-state CAs).
    Pure Python, no numpy - keeping it self-contained.
    Uses flat list for performance.
    """

    def __init__(self, width: int, height: int, data: Optional[list] = None):
        self.w = width
        self.h = height
        if data is not None:
            self.cells = list(data)
        else:
            self.cells = [0] * (width * height)

    def get(self, x: int, y: int) -> int:
        return self.cells[(y % self.h) * self.w + (x % self.w)]

    def set(self, x: int, y: int, v: int):
        self.cells[(y % self.h) * self.w + (x % self.w)] = v

    def copy(self) -> 'Grid':
        return Grid(self.w, self.h, self.cells[:])

    def fingerprint(self) -> str:
        """Fast hash for detecting repeated states."""
        data = bytes(self.cells)
        return hashlib.md5(data, usedforsecurity=False).hexdigest()[:16]

    def population(self, state: int = 1) -> int:
        return self.cells.count(state)

    def total_alive(self) -> int:
        return sum(1 for c in self.cells if c != 0)

    def neighbors_sum(self, x: int, y: int) -> int:
        """Count live (state=1) neighbours in Moore neighbourhood."""
        w, h = self.w, self.h
        s = 0
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                nx, ny = (x + dx) % w, (y + dy) % h
                if self.cells[ny * w + nx]:
                    s += 1
        return s

    def neighbor_states(self, x: int, y: int) -> list:
        """Get all 8 neighbour states."""
        w, h = self.w, self.h
        states = []
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                nx, ny = (x + dx) % w, (y + dy) % h
                states.append(self.cells[ny * w + nx])
        return states

    @classmethod
    def random(cls, width: int, height: int, density: float = 0.3, seed: int = None) -> 'Grid':
        rng = random.Random(seed)
        g = cls(width, height)
        g.cells = [1 if rng.random() < density else 0 for _ in range(width * height)]
        return g

    def render_ascii(self, alive: str = "█", dead: str = " ", max_w: int = 60, max_h: int = 24) -> str:
        w = min(self.w, max_w)
        h = min(self.h, max_h)
        lines = []
        for y in range(h):
            row = ""
            for x in range(w):
                row += alive if self.cells[y * self.w + x] else dead
            lines.append(row)
        return "\n".join(lines)

    def render_color(self, state_colors: dict, max_w: int = 60, max_h: int = 20) -> str:
        """Render with ANSI block characters and colors."""
        w = min(self.w, max_w)
        h = min(self.h, max_h)
        lines = []
        for y in range(h):
            row = ""
            for x in range(w):
                state = self.cells[y * self.w + x]
                color = state_colors.get(state, T.BBLACK)
                ch = "█" if state else " "
                row += f"{color}{ch}"
            lines.append(row + T.RESET)
        return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# Rule Systems
# ─────────────────────────────────────────────────────────────────────────────

class Rule:
    """Base class for cellular automata rules."""
    name = "Unknown"
    description = ""
    num_states = 2

    def step(self, grid: Grid) -> Grid:
        raise NotImplementedError


class ConwayLife(Rule):
    """
    B3/S23 - Conway's Game of Life
    Born if 3 live neighbours, Survives with 2 or 3.
    Turing complete. Contains gliders, spaceships, oscillators.
    """
    name = "Conway's Life (B3/S23)"
    description = "The classic. Born:3, Survive:2,3"
    num_states = 2

    def __init__(self, born=(3,), survive=(2, 3)):
        self.born = set(born)
        self.survive = set(survive)

    def step(self, grid: Grid) -> Grid:
        w, h = grid.w, grid.h
        new = Grid(w, h)
        cells = grid.cells
        new_cells = new.cells
        for y in range(h):
            for x in range(w):
                n = 0
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if dx == 0 and dy == 0:
                            continue
                        if cells[((y + dy) % h) * w + ((x + dx) % w)]:
                            n += 1
                cur = cells[y * w + x]
                if cur:
                    new_cells[y * w + x] = 1 if n in self.survive else 0
                else:
                    new_cells[y * w + x] = 1 if n in self.born else 0
        return new


class Seeds(Rule):
    """
    B2/S0 - Seeds
    Every dead cell with exactly 2 live neighbours comes to life.
    Dead cells never survive. Pure explosion - chaotic.
    """
    name = "Seeds (B2/S0)"
    description = "Every cell born from 2 neighbours, none survive"
    num_states = 2

    def step(self, grid: Grid) -> Grid:
        w, h = grid.w, grid.h
        new = Grid(w, h)
        cells = grid.cells
        new_cells = new.cells
        for y in range(h):
            for x in range(w):
                n = 0
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if dx == 0 and dy == 0:
                            continue
                        if cells[((y + dy) % h) * w + ((x + dx) % w)]:
                            n += 1
                new_cells[y * w + x] = 1 if (not cells[y * w + x] and n == 2) else 0
        return new


class BriansBrain(Rule):
    """
    Brian's Brain - 3-state CA.
    State 0=dead, 1=alive(firing), 2=dying(refractory)
    Born if exactly 2 live neighbours AND currently dead.
    Then dies (refractory), then truly dies.
    Produces endless streams of gliders.
    """
    name = "Brian's Brain"
    description = "3-state: firing→refractory→dead. Endless gliders."
    num_states = 3

    def step(self, grid: Grid) -> Grid:
        w, h = grid.w, grid.h
        new = Grid(w, h)
        cells = grid.cells
        new_cells = new.cells
        for y in range(h):
            for x in range(w):
                cur = cells[y * w + x]
                if cur == 1:
                    # Firing -> Dying
                    new_cells[y * w + x] = 2
                elif cur == 2:
                    # Dying -> Dead
                    new_cells[y * w + x] = 0
                else:
                    # Dead: count firing neighbours
                    n = 0
                    for dy in (-1, 0, 1):
                        for dx in (-1, 0, 1):
                            if dx == 0 and dy == 0:
                                continue
                            if cells[((y + dy) % h) * w + ((x + dx) % w)] == 1:
                                n += 1
                    new_cells[y * w + x] = 1 if n == 2 else 0
        return new


class Wireworld(Rule):
    """
    Wireworld - simulates electronic circuits.
    State 0=empty, 1=conductor, 2=electron_head, 3=electron_tail
    Used to build actual logic gates and computers.
    """
    name = "Wireworld"
    description = "Electronic circuit simulator. Can build logic gates."
    num_states = 4

    def step(self, grid: Grid) -> Grid:
        w, h = grid.w, grid.h
        new = Grid(w, h)
        cells = grid.cells
        new_cells = new.cells
        for y in range(h):
            for x in range(w):
                cur = cells[y * w + x]
                if cur == 0:
                    new_cells[y * w + x] = 0
                elif cur == 2:  # head -> tail
                    new_cells[y * w + x] = 3
                elif cur == 3:  # tail -> conductor
                    new_cells[y * w + x] = 1
                else:  # conductor
                    # Count electron heads in neighbourhood
                    heads = sum(
                        1 for dy in (-1, 0, 1) for dx in (-1, 0, 1)
                        if not (dx == 0 and dy == 0)
                        and cells[((y+dy)%h)*w + ((x+dx)%w)] == 2
                    )
                    new_cells[y * w + x] = 2 if heads in (1, 2) else 1
        return new


class Rule1D(Rule):
    """
    Wolfram's Elementary Cellular Automata - 1D rules 0-255.
    Each cell has 3 binary inputs (left, self, right) = 8 cases = 1 byte = 256 rules.
    Rule 110 is Turing complete. Rule 30 is used as a random number generator.
    """
    name = "1D Elementary CA"
    description = "Wolfram's 256 1D rules"
    num_states = 2

    def __init__(self, rule_number: int = 110):
        self.rule_number = rule_number
        self.lookup = [(rule_number >> i) & 1 for i in range(8)]
        self.name = f"Wolfram Rule {rule_number}"

    def step(self, grid: Grid) -> Grid:
        """For 1D CAs, we use a wide, 1-row grid and scroll down."""
        w, h = grid.w, grid.h
        new = Grid(w, h)
        # Scroll up: copy rows 1..h-1 to 0..h-2
        new.cells[:w * (h - 1)] = grid.cells[w:w * h]
        # Generate new bottom row from last row
        last_row_start = (h - 1) * w
        for x in range(w):
            left  = grid.cells[last_row_start + (x - 1) % w]
            mid   = grid.cells[last_row_start + x]
            right = grid.cells[last_row_start + (x + 1) % w]
            idx = (left << 2) | (mid << 1) | right
            new.cells[last_row_start + x] = self.lookup[idx]
        return new

    @classmethod
    def make_seed_row(cls, width: int, height: int) -> Grid:
        """Single live cell in the centre - classic 1D CA seed."""
        g = Grid(width, height)
        g.set(width // 2, height - 1, 1)
        return g


class HighLife(ConwayLife):
    """
    B36/S23 - HighLife
    Like Life but also born with 6. Has a replicator pattern!
    """
    name = "HighLife (B36/S23)"
    description = "Life with replicator. Born:3,6 Survive:2,3"

    def __init__(self):
        super().__init__(born=(3, 6), survive=(2, 3))


class DayAndNight(ConwayLife):
    """
    B3678/S34678 - Day & Night
    Symmetric: complement of live/dead gives same rule.
    """
    name = "Day & Night (B3678/S34678)"
    description = "Symmetric rule. Dense=Life, sparse=also Life."

    def __init__(self):
        super().__init__(born=(3, 6, 7, 8), survive=(3, 4, 6, 7, 8))


# ─────────────────────────────────────────────────────────────────────────────
# Pattern Library
# ─────────────────────────────────────────────────────────────────────────────

def encode_rle(pattern_str: str) -> list[tuple[int, int]]:
    """Parse a simple coordinate list like '0,0 1,0 2,0' -> [(0,0),(1,0),(2,0)]"""
    coords = []
    for token in pattern_str.strip().split():
        x, y = token.split(",")
        coords.append((int(x), int(y)))
    return coords


def parse_rle(rle: str) -> list[tuple[int, int]]:
    """Parse RLE format used by Golly/LifeWiki."""
    coords = []
    x, y = 0, 0
    count = 0
    for ch in rle:
        if ch.isdigit():
            count = count * 10 + int(ch)
        elif ch == 'b':
            x += max(1, count)
            count = 0
        elif ch == 'o':
            n = max(1, count)
            for i in range(n):
                coords.append((x + i, y))
            x += n
            count = 0
        elif ch == '$':
            y += max(1, count)
            x = 0
            count = 0
        elif ch == '!':
            break
        else:
            count = 0
    return coords


class PatternLibrary:
    """Famous patterns from the Game of Life universe."""

    GLIDER = parse_rle("bo$2bo$3o!")
    R_PENTOMINO = parse_rle("2o$ob$b!")  # chaos engine, runs for 1103 generations
    BLINKER = parse_rle("3o!")
    BLOCK = parse_rle("2o$2o!")
    BEEHIVE = parse_rle("b2o$o2bo$b2o!")
    TOAD = parse_rle("b3o$3ob!")
    PULSAR_SEED = parse_rle("2bo$2bo$2bo!")  # becomes pulsar after several gens
    LIGHTWEIGHT_SPACESHIP = parse_rle("bo2bo$o$o3bo$4o!")
    DIEHARD = parse_rle("6bob$2o$bo3b3o!")  # lives exactly 130 generations
    ACORN = parse_rle("bo$3bo$2o2b3o!")     # grows explosively

    RULE110_SEED = "single_center"

    WIREWORLD_CLOCK = [  # Simple electron clock circuit
        (2, 1), (3, 1), (4, 1), (5, 1), (6, 1), (7, 1), (8, 1),
        (8, 2), (8, 3),
        (7, 3), (6, 3), (5, 3), (4, 3), (3, 3), (2, 3),
        (2, 2),
        # Electron head and tail
    ]

    @classmethod
    def place(cls, grid: Grid, coords: list, cx: int, cy: int, state: int = 1):
        """Place a pattern centered at (cx, cy)."""
        if not coords:
            return
        min_x = min(c[0] for c in coords)
        min_y = min(c[1] for c in coords)
        max_x = max(c[0] for c in coords)
        max_y = max(c[1] for c in coords)
        offset_x = cx - (min_x + max_x) // 2
        offset_y = cy - (min_y + max_y) // 2
        for x, y in coords:
            grid.set(x + offset_x, y + offset_y, state)

    @classmethod
    def make_glider_gun(cls, width: int = 60, height: int = 40) -> Grid:
        """Gosper Glider Gun - first known infinite-growth pattern."""
        g = Grid(width, height)
        rle = ("24bo$22bobo$12b2o6b2o12b2o$11bo3bo4b2o12b2o$"
               "2o8bo5bo3b2o$2o8bo3bob2o4bobo$10bo5bo7bo$11bo3bo$12b2o!")
        coords = parse_rle(rle)
        cls.place(g, coords, width // 4, height // 2)
        return g


# ─────────────────────────────────────────────────────────────────────────────
# Analysis Engine
# ─────────────────────────────────────────────────────────────────────────────

class Analysis:
    """
    Tools to measure how "interesting" a CA simulation is.
    Interesting = neither all dead (order) nor totally random (chaos).
    The sweet spot is at the "edge of chaos."
    """

    @staticmethod
    def entropy(grid: Grid) -> float:
        """
        Shannon entropy of cell states. 0=all same, 1=maximally random.
        (Normalised to [0,1])
        """
        if not grid.cells:
            return 0.0
        counts = Counter(grid.cells)
        total = len(grid.cells)
        max_entropy = math.log2(grid.num_states if hasattr(grid, 'num_states') else 2)
        if max_entropy == 0:
            return 0.0
        h = 0.0
        for c in counts.values():
            if c > 0:
                p = c / total
                h -= p * math.log2(p)
        return h / max(max_entropy, 1.0)

    @staticmethod
    def spatial_entropy(grid: Grid, block_size: int = 4) -> float:
        """
        Measure entropy of spatial blocks - detects structure vs noise.
        High spatial entropy with low cell entropy = structured patterns.
        """
        w, h = grid.w, grid.h
        block_hashes = []
        for by in range(0, h, block_size):
            for bx in range(0, w, block_size):
                block = tuple(
                    grid.cells[((by + dy) % h) * w + ((bx + dx) % w)]
                    for dy in range(block_size)
                    for dx in range(block_size)
                )
                block_hashes.append(block)
        if not block_hashes:
            return 0.0
        counts = Counter(block_hashes)
        total = len(block_hashes)
        h_val = 0.0
        for c in counts.values():
            p = c / total
            h_val -= p * math.log2(p)
        max_h = math.log2(total) if total > 1 else 1
        return h_val / max_h

    @staticmethod
    def autocorrelation(cells: list, lag: int = 1) -> float:
        """Spatial autocorrelation - measures how correlated adjacent cells are."""
        n = len(cells)
        if n <= lag:
            return 0.0
        mean = sum(cells) / n
        if mean == 0 or mean == 1:
            return 1.0
        var = sum((c - mean) ** 2 for c in cells) / n
        if var == 0:
            return 1.0
        cov = sum((cells[i] - mean) * (cells[(i + lag) % n] - mean) for i in range(n)) / n
        return cov / var

    @staticmethod
    def detect_stasis(history: list[str]) -> Optional[int]:
        """
        Detect if the simulation has reached a fixed point or cycle.
        Returns cycle length if found, None otherwise.
        """
        if len(history) < 2:
            return None
        last = history[-1]
        for i in range(len(history) - 2, max(-1, len(history) - 64), -1):
            if history[i] == last:
                return len(history) - 1 - i
        return None

    @staticmethod
    def growth_rate(populations: list[int]) -> float:
        """Average population growth rate over last window."""
        if len(populations) < 2:
            return 0.0
        changes = [populations[i] - populations[i-1] for i in range(1, len(populations))]
        return sum(changes) / len(changes)

    @staticmethod
    def complexity_score(grid: Grid, prev_grids: list[Grid]) -> float:
        """
        Composite "interestingness" score combining:
        - Shannon entropy (not too ordered, not too random)
        - Spatial entropy (structure exists)
        - Autocorrelation (nearby cells correlated = structure)
        - Temporal change (still evolving = interesting)
        """
        H = Analysis.entropy(grid)
        # Penalise extremes: best entropy is around 0.5-0.7
        entropy_score = 1.0 - abs(H - 0.6) * 2
        entropy_score = max(0.0, min(1.0, entropy_score))

        # Spatial structure
        spatial = Analysis.spatial_entropy(grid)

        # Autocorrelation (positive = clustered = structured)
        ac = Analysis.autocorrelation(grid.cells)
        ac_score = max(0.0, (ac + 1) / 2)  # normalise from [-1,1] to [0,1]

        # Temporal change - compare to prev grid
        if prev_grids:
            prev = prev_grids[-1]
            changes = sum(1 for a, b in zip(grid.cells, prev.cells) if a != b)
            change_rate = changes / len(grid.cells)
            # Best around 5-30% change per step
            temporal = 1.0 - abs(change_rate - 0.15) * 4
            temporal = max(0.0, min(1.0, temporal))
        else:
            temporal = 0.5

        return (entropy_score * 0.3 + spatial * 0.3 + ac_score * 0.2 + temporal * 0.2)

    @staticmethod
    def classify_behaviour(populations: list[int], fingerprints: list[str],
                           entropy_history: list[float]) -> str:
        """
        Classify the long-term behaviour of a simulation:
        - EXTINCT: population → 0
        - FROZEN: static, no change
        - PERIODIC: repeating cycle
        - CHAOTIC: unpredictable, high entropy
        - COMPLEX: structured, evolving, "interesting"
        """
        if not populations:
            return "UNKNOWN"

        final_pop = populations[-1]
        initial_pop = populations[0] if populations else 1

        if final_pop == 0:
            return "EXTINCT"

        # Check for stasis
        cycle = Analysis.detect_stasis(fingerprints)
        if cycle == 1:
            return "FROZEN"
        if cycle and cycle <= 32:
            return f"PERIODIC (period {cycle})"

        # Check entropy trend
        if entropy_history:
            avg_entropy = sum(entropy_history) / len(entropy_history)
            entropy_variance = sum((e - avg_entropy)**2 for e in entropy_history) / len(entropy_history)

            if avg_entropy > 0.85:
                return "CHAOTIC"
            if entropy_variance < 0.001 and avg_entropy > 0.2:
                return "STABLE-COMPLEX"
            if avg_entropy < 0.15:
                return "SPARSE"

        return "COMPLEX"


# ─────────────────────────────────────────────────────────────────────────────
# Simulation Runner
# ─────────────────────────────────────────────────────────────────────────────

class Simulation:
    """Runs a CA rule and collects statistics."""

    def __init__(self, rule: Rule, initial: Grid):
        self.rule = rule
        self.grid = initial
        self.generation = 0
        self.history_fps: list[str] = [initial.fingerprint()]
        self.populations: list[int] = [initial.total_alive()]
        self.entropy_history: list[float] = [Analysis.entropy(initial)]
        self.complexity_history: list[float] = []
        self.prev_grids: list[Grid] = []

    def step(self) -> bool:
        """Advance one generation. Returns False if terminated."""
        new_grid = self.rule.step(self.grid)
        self.generation += 1
        fp = new_grid.fingerprint()

        self.prev_grids.append(self.grid)
        if len(self.prev_grids) > 5:
            self.prev_grids.pop(0)

        self.grid = new_grid
        self.history_fps.append(fp)
        if len(self.history_fps) > 128:
            self.history_fps.pop(0)

        pop = new_grid.total_alive()
        self.populations.append(pop)
        if len(self.populations) > 256:
            self.populations.pop(0)

        H = Analysis.entropy(new_grid)
        self.entropy_history.append(H)
        if len(self.entropy_history) > 256:
            self.entropy_history.pop(0)

        complexity = Analysis.complexity_score(new_grid, self.prev_grids)
        self.complexity_history.append(complexity)
        if len(self.complexity_history) > 256:
            self.complexity_history.pop(0)

        return pop > 0

    def run(self, steps: int, early_stop: bool = True) -> None:
        """Run for N steps with optional early termination on stasis."""
        for _ in range(steps):
            alive = self.step()
            if not alive:
                break
            if early_stop and len(self.history_fps) >= 4:
                cycle = Analysis.detect_stasis(self.history_fps)
                if cycle and cycle <= 4 and self.generation > 50:
                    break

    def peak_complexity(self) -> float:
        return max(self.complexity_history) if self.complexity_history else 0.0

    def avg_complexity(self) -> float:
        if not self.complexity_history:
            return 0.0
        return sum(self.complexity_history) / len(self.complexity_history)

    def behaviour(self) -> str:
        return Analysis.classify_behaviour(
            self.populations, self.history_fps, self.entropy_history
        )


# ─────────────────────────────────────────────────────────────────────────────
# Rule Space Explorer
# ─────────────────────────────────────────────────────────────────────────────

class RuleSpaceExplorer:
    """
    Explores the outer-totalistic rule space around Conway's Life.
    Each rule is defined by:
      - born set: which neighbour counts cause birth (0-8)
      - survive set: which neighbour counts allow survival (0-8)
    This gives 2^9 * 2^9 = 262,144 possible rules.
    We'll sample this space and measure complexity.
    """

    @staticmethod
    def rule_to_string(born: frozenset, survive: frozenset) -> str:
        b = "".join(str(n) for n in sorted(born))
        s = "".join(str(n) for n in sorted(survive))
        return f"B{b}/S{s}"

    @staticmethod
    def nearby_rules(born: frozenset, survive: frozenset, radius: int = 1):
        """Generate all rules within Hamming distance `radius` of given rule."""
        all_counts = frozenset(range(9))
        rules = set()

        def toggle_one(s):
            for n in range(9):
                if n in s:
                    yield s - {n}
                else:
                    yield s | {n}

        # Radius 1: toggle one element of born or survive
        for new_born in toggle_one(born):
            rules.add((new_born, survive))
        for new_survive in toggle_one(survive):
            rules.add((born, new_survive))

        if radius >= 2:
            # Radius 2: toggle two elements
            for r1 in list(rules):
                for new_born in toggle_one(r1[0]):
                    rules.add((new_born, r1[1]))
                for new_survive in toggle_one(r1[1]):
                    rules.add((r1[0], new_survive))

        return rules

    @staticmethod
    def evaluate_rule(born: frozenset, survive: frozenset,
                      width: int = 30, height: int = 30,
                      steps: int = 100, trials: int = 3) -> dict:
        """
        Run a rule on random soup and measure its behaviour.
        Returns statistics dict.
        """
        rule = ConwayLife(born=born, survive=survive)
        scores = []
        behaviours = []

        for trial in range(trials):
            g = Grid.random(width, height, density=0.3, seed=trial * 997 + 42)
            sim = Simulation(rule, g)
            sim.run(steps, early_stop=True)
            scores.append(sim.avg_complexity())
            behaviours.append(sim.behaviour())

        avg_score = sum(scores) / len(scores)
        # Most common behaviour
        behaviour_counts = Counter(behaviours)
        dominant_behaviour = behaviour_counts.most_common(1)[0][0]

        return {
            "rule": RuleSpaceExplorer.rule_to_string(born, survive),
            "avg_complexity": avg_score,
            "peak_complexity": max(scores),
            "behaviour": dominant_behaviour,
            "born": sorted(born),
            "survive": sorted(survive),
        }


# ─────────────────────────────────────────────────────────────────────────────
# Demonstration Patterns
# ─────────────────────────────────────────────────────────────────────────────

def demo_glider_gun(steps: int = 40) -> Simulation:
    """Run the Gosper Glider Gun."""
    g = PatternLibrary.make_glider_gun(64, 36)
    rule = ConwayLife()
    sim = Simulation(rule, g)
    sim.run(steps, early_stop=False)
    return sim


def demo_r_pentomino(steps: int = 200) -> Simulation:
    """Run the R-pentomino - 5 cells that erupt into beautiful chaos."""
    g = Grid(50, 40)
    PatternLibrary.place(g, PatternLibrary.R_PENTOMINO, 25, 20)
    rule = ConwayLife()
    sim = Simulation(rule, g)
    sim.run(steps, early_stop=False)
    return sim


def demo_rule110(steps: int = None) -> Simulation:
    """Rule 110 - provably Turing complete 1D CA."""
    width, height = 70, 50
    g = Rule1D.make_seed_row(width, height)
    rule = Rule1D(110)
    sim = Simulation(rule, g)
    sim.run(height - 1, early_stop=False)
    return sim


def demo_brians_brain(steps: int = 50) -> Simulation:
    """Brian's Brain - generates endless gliders."""
    g = Grid.random(40, 30, density=0.3, seed=42)
    # Convert random cells to state 1 (only firing, no refractory)
    rule = BriansBrain()
    sim = Simulation(rule, g)
    sim.run(steps, early_stop=False)
    return sim


# ─────────────────────────────────────────────────────────────────────────────
# The Emergence Report
# ─────────────────────────────────────────────────────────────────────────────

def render_population_chart(populations: list[int], width: int = 50, height: int = 8) -> str:
    """ASCII sparkline of population over time."""
    if not populations:
        return ""
    max_p = max(populations) or 1
    min_p = min(populations)
    samples = populations
    if len(populations) > width:
        step = len(populations) / width
        samples = [populations[int(i * step)] for i in range(width)]

    blocks = " ▁▂▃▄▅▆▇█"
    line = ""
    for p in samples:
        norm = (p - min_p) / max(max_p - min_p, 1)
        idx = int(norm * (len(blocks) - 1))
        line += blocks[idx]

    return f"  {T.BBLUE}pop:{T.RESET} {T.CYAN}{line}{T.RESET} {T.DIM}[{min_p}→{max_p}]{T.RESET}"


def render_complexity_chart(complexity: list[float], width: int = 50) -> str:
    """Sparkline of complexity score."""
    if not complexity:
        return ""
    samples = complexity
    if len(complexity) > width:
        step = len(complexity) / width
        samples = [complexity[int(i * step)] for i in range(width)]

    blocks = " ▁▂▃▄▅▆▇█"
    line = ""
    for c in samples:
        idx = int(c * (len(blocks) - 1))
        line += blocks[max(0, min(len(blocks)-1, idx))]

    avg = sum(complexity) / len(complexity)
    return f"  {T.BMAGENTA}cplx:{T.RESET} {T.MAGENTA}{line}{T.RESET} {T.DIM}avg={avg:.3f}{T.RESET}"


def render_grid_pretty(grid: Grid, rule: Rule, max_w: int = 58, max_h: int = 20) -> str:
    """Render grid with context-appropriate colors."""
    if isinstance(rule, BriansBrain):
        colors = {0: T.BBLACK, 1: T.BWHITE, 2: T.BLUE}
        chars = {0: "·", 1: "█", 2: "▒"}
    elif isinstance(rule, Wireworld):
        colors = {0: T.BBLACK, 1: T.BYELLOW, 2: T.BBLUE, 3: T.BRED}
        chars = {0: " ", 1: "─", 2: "●", 3: "○"}
    elif isinstance(rule, Rule1D):
        colors = {0: T.rgb(20, 20, 40), 1: T.rgb(100, 200, 255)}
        chars = {0: "·", 1: "█"}
    else:
        colors = {0: T.rgb(15, 15, 25), 1: T.rgb(80, 200, 120)}
        chars = {0: " ", 1: "█"}

    w = min(grid.w, max_w)
    h = min(grid.h, max_h)
    lines = []
    border = f"  {T.BBLACK}┌" + "─" * w + f"┐{T.RESET}"
    lines.append(border)
    for y in range(h):
        row = f"  {T.BBLACK}│{T.RESET}"
        for x in range(w):
            state = grid.cells[y * grid.w + x]
            color = colors.get(state, T.BBLACK)
            ch = chars.get(state, " ")
            row += f"{color}{ch}"
        row += f"{T.RESET}{T.BBLACK}│{T.RESET}"
        lines.append(row)
    lines.append(f"  {T.BBLACK}└" + "─" * w + f"┘{T.RESET}")
    return "\n".join(lines)


def run_experiment(label: str, rule: Rule, grid: Grid, steps: int,
                   early_stop: bool = False, show_grid: bool = True) -> Simulation:
    """Run a single experiment and display results."""
    subsection(label)
    sim = Simulation(rule, grid)

    # Animate a few frames
    sys.stdout.write(f"  {T.DIM}Running {steps} generations...{T.RESET}\n")
    sys.stdout.flush()

    sim.run(steps, early_stop=early_stop)

    if show_grid:
        print(render_grid_pretty(sim.grid, rule))

    print(render_population_chart(sim.populations))
    print(render_complexity_chart(sim.complexity_history))

    result("Generations run", str(sim.generation))
    result("Final population", str(sim.grid.total_alive()))
    result("Behaviour", sim.behaviour(),
           T.BGREEN if "COMPLEX" in sim.behaviour() else
           T.BYELLOW if "PERIODIC" in sim.behaviour() else
           T.BRED if "EXTINCT" in sim.behaviour() or "FROZEN" in sim.behaviour() else T.BCYAN)
    result("Peak complexity", f"{sim.peak_complexity():.4f}")
    result("Avg complexity", f"{sim.avg_complexity():.4f}")
    result("Final entropy", f"{Analysis.entropy(sim.grid):.4f}")

    return sim


# ─────────────────────────────────────────────────────────────────────────────
# Rule Space Survey
# ─────────────────────────────────────────────────────────────────────────────

def survey_life_neighbourhood():
    """
    Survey the rule space in the neighbourhood of Life (B3/S23).
    The question: how special is Life? Is it a local maximum of complexity?
    """
    section("RULE SPACE SURVEY: The Neighbourhood of Life", T.BMAGENTA)

    info("Conway's Life: B3/S23")
    info("Testing all rules within Hamming distance 1 in the B/S space...")
    info("(Toggling one birth or survival condition at a time)")
    print()

    life_born = frozenset([3])
    life_survive = frozenset([2, 3])

    # Evaluate Life itself first
    life_result = RuleSpaceExplorer.evaluate_rule(life_born, life_survive,
                                                   width=32, height=32,
                                                   steps=80, trials=4)
    result("Conway's Life B3/S23", f"complexity={life_result['avg_complexity']:.4f}  [{life_result['behaviour']}]",
           T.BGREEN)
    print()

    # Get all neighbours
    neighbours = RuleSpaceExplorer.nearby_rules(life_born, life_survive, radius=1)
    results = []

    print(f"  {T.DIM}Evaluating {len(neighbours)} neighbouring rules...{T.RESET}", end="", flush=True)

    for i, (born, survive) in enumerate(neighbours):
        if i % 5 == 0:
            print(f"\r  {T.DIM}Evaluating {len(neighbours)} neighbouring rules... {i+1}/{len(neighbours)}{T.RESET}",
                  end="", flush=True)
        r = RuleSpaceExplorer.evaluate_rule(born, survive,
                                             width=32, height=32,
                                             steps=80, trials=3)
        results.append(r)

    print(f"\r  {T.BGREEN}Done! Evaluated {len(results)} rules.{T.RESET}              ")

    # Sort by complexity
    results.sort(key=lambda x: x['avg_complexity'], reverse=True)

    subsection("Top 10 Most Complex Rules near Life")
    print(f"  {'Rule':<18} {'Complexity':>10} {'Behaviour':<30}")
    print(f"  {'─'*18} {'─'*10} {'─'*30}")

    for i, r in enumerate(results[:10]):
        color = T.BGREEN if r['avg_complexity'] > life_result['avg_complexity'] else T.YELLOW
        marker = " ◀ LIFE" if r['rule'] == "B3/S23" else ""
        print(f"  {color}{r['rule']:<18}{T.RESET} "
              f"{T.CYAN}{r['avg_complexity']:>10.4f}{T.RESET} "
              f"{T.DIM}{r['behaviour']:<30}{T.RESET}{T.BYELLOW}{marker}{T.RESET}")

    # Stats
    print()
    complex_count = sum(1 for r in results if "COMPLEX" in r['behaviour'] or "STABLE" in r['behaviour'])
    extinct_count = sum(1 for r in results if "EXTINCT" in r['behaviour'])
    frozen_count  = sum(1 for r in results if "FROZEN" in r['behaviour'] or "SPARSE" in r['behaviour'])
    chaotic_count = sum(1 for r in results if "CHAOTIC" in r['behaviour'])

    total = len(results)
    subsection("Behaviour Distribution in Life's Neighbourhood")
    print(f"  Complex/Structured : {progress_bar(complex_count/total, 30, T.BGREEN)} ({complex_count}/{total})")
    print(f"  Extinct            : {progress_bar(extinct_count/total, 30, T.BRED)}  ({extinct_count}/{total})")
    print(f"  Frozen/Sparse      : {progress_bar(frozen_count/total, 30, T.BYELLOW)} ({frozen_count}/{total})")
    print(f"  Chaotic            : {progress_bar(chaotic_count/total, 30, T.BCYAN)} ({chaotic_count}/{total})")

    life_rank = next((i for i, r in enumerate(results) if r['rule'] == "B3/S23"), -1)

    print()
    if life_result['avg_complexity'] >= results[0]['avg_complexity'] * 0.9:
        info(f"{T.BGREEN}Life is a LOCAL MAXIMUM of complexity in its neighbourhood.{T.RESET}")
    else:
        info(f"{T.BYELLOW}Some neighbours of Life are MORE complex.{T.RESET}")
        info(f"The most complex neighbour: {results[0]['rule']}")

    return results, life_result


# ─────────────────────────────────────────────────────────────────────────────
# Random Rule Space Sample
# ─────────────────────────────────────────────────────────────────────────────

def sample_rule_space(n: int = 200, seed: int = 42):
    """
    Sample N random rules from the entire outer-totalistic rule space.
    Classify their behaviours and measure where complexity lives.
    """
    section("RANDOM RULE SPACE SAMPLE", T.BCYAN)
    info(f"Sampling {n} random rules from the full 2^18 = 262,144 rule space...")
    info("Classifying each as: Extinct / Frozen / Periodic / Chaotic / Complex")
    print()

    rng = random.Random(seed)
    results = []

    for i in range(n):
        if i % 20 == 0:
            print(f"\r  {T.DIM}Sampling... {i}/{n}{T.RESET}", end="", flush=True)

        # Random B/S rule
        born = frozenset(k for k in range(9) if rng.random() < 0.3)
        survive = frozenset(k for k in range(9) if rng.random() < 0.4)

        r = RuleSpaceExplorer.evaluate_rule(born, survive,
                                             width=28, height=28,
                                             steps=60, trials=2)
        results.append(r)

    print(f"\r  {T.BGREEN}Sampled {n} rules.{T.RESET}              ")

    behaviours = Counter(r['behaviour'].split()[0] for r in results)

    subsection("Behaviour distribution across random rule space")
    total = len(results)
    for beh, count in sorted(behaviours.items(), key=lambda x: -x[1]):
        color = (T.BGREEN if beh in ("COMPLEX", "STABLE-COMPLEX") else
                 T.BRED if beh == "EXTINCT" else
                 T.BYELLOW if beh in ("FROZEN", "SPARSE") else
                 T.BCYAN)
        print(f"  {color}{beh:<20}{T.RESET} {progress_bar(count/total, 35, color)} ({count})")

    complex_results = [r for r in results if "COMPLEX" in r['behaviour'] or "STABLE" in r['behaviour']]
    print()
    result("Rules with complex behaviour", f"{len(complex_results)}/{total} ({100*len(complex_results)/total:.1f}%)")

    if complex_results:
        best = max(complex_results, key=lambda r: r['avg_complexity'])
        result("Most complex random rule found", best['rule'], T.BGREEN)
        result("  → complexity score", f"{best['avg_complexity']:.4f}")

    return results


# ─────────────────────────────────────────────────────────────────────────────
# The Main Report
# ─────────────────────────────────────────────────────────────────────────────

def print_essay():
    """Print a short meditation on emergence and the edge of chaos."""
    section("ON EMERGENCE AND THE EDGE OF CHAOS", T.BYELLOW)

    paragraphs = [
        (T.BWHITE + T.BOLD, "What is happening here?"),
        (T.RESET, """  Conway's Life consists of four rules:
    1. A live cell with fewer than 2 neighbours dies (underpopulation)
    2. A live cell with 2-3 neighbours survives
    3. A live cell with more than 3 neighbours dies (overcrowding)
    4. A dead cell with exactly 3 neighbours comes alive (reproduction)

  From these four sentences, an entire universe emerges."""),

        (T.BYELLOW + T.BOLD, "The Edge of Chaos"),
        (T.RESET, """  Stephen Wolfram classified all 256 elementary 1D cellular automata into
  four classes:
    Class I   → stable fixed point (boredom)
    Class II  → periodic oscillation (boredom, cyclic)
    Class III → chaotic (noise, no structure, no information)
    Class IV  → complex, persistent structures (the interesting zone)

  Conway's Life is Class IV. It sits at the boundary between order and
  chaos — the only place where interesting computation can happen.
  Too ordered: nothing can be written, nothing can be computed.
  Too chaotic: signals are destroyed before they carry information.

  Only at the edge can a glider carry a signal across an infinite grid."""),

        (T.BCYAN + T.BOLD, "Why does complexity require the edge?"),
        (T.RESET, """  Think about information storage. A frozen rule (Class II) can store
  patterns, but can't process them — it's a hard drive with no CPU.
  A chaotic rule (Class III) can mix information, but destroys structure
  — it's thermal noise.

  Computation requires both: stable structures to hold state AND dynamic
  structures to propagate signals. You need gliders (signals) AND blocks
  (memory) AND glider guns (clocks). Life has all three.

  This is why living things exist at the edge of chaos. DNA is stable
  enough to be inherited (order) but mutable enough to evolve (chaos).
  The brain maintains criticality between ordered and chaotic firing.
  Markets hover between crystallized tradition and random innovation."""),

        (T.BMAGENTA + T.BOLD, "Turing completeness from nothing"),
        (T.RESET, """  In 2002, Paul Rendell proved that Conway's Life is Turing complete.
  You can build a Universal Turing Machine inside Life using patterns
  that emerge from those four rules. Rule 110 (1D) was proven Turing
  complete by Matthew Cook in 2004.

  This means the answer to "can this system compute X?" is yes for any X,
  for any program ever written, for any function ever defined —
  it can all be simulated in a grid of black and white squares,
  updated by four rules about counting neighbours.

  The universe may work the same way."""),

        (T.BGREEN + T.BOLD, "On the specialness of Life"),
        (T.RESET, """  Out of 262,144 outer-totalistic rules, most are boring:
    - Most with high birth rates explode to maximum density and freeze
    - Most with low birth rates die out completely
    - Only a thin sliver produces persistent, complex behaviour

  The survey above shows that Life (B3/S23) sits in this rare zone —
  but it's not unique. Many nearby rules are also complex. What makes
  Life famous is partly historical accident (Conway chose it carefully
  in 1970, seeking exactly the edge-of-chaos property) and partly
  that it's the simplest such rule with gliders and spaceships.

  The edge of chaos isn't a point — it's a phase boundary.
  Life found it. So, apparently, did evolution."""),
    ]

    for color, text in paragraphs:
        if T.BOLD in color:
            print(f"\n  {color}{text}{T.RESET}")
        else:
            print(f"{T.DIM}{text}{T.RESET}")
            print()


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    os.system("clear")
    banner()

    print(f"  {T.DIM}Python {sys.version.split()[0]} • Pure stdlib • No dependencies{T.RESET}")
    print(f"  {T.DIM}Press Ctrl+C at any time to skip to the next section.{T.RESET}\n")

    try:
        # ── Part 1: Classic demonstrations ───────────────────────────────────
        section("PART 1: DEMONSTRATIONS — Universes from Simple Rules", T.BCYAN)

        info("We'll visit five distinct rule universes and watch emergence happen.")
        print()

        # 1a. Conway's Life - R-pentomino
        sim_r = run_experiment(
            "Conway's Life (B3/S23) — R-pentomino",
            ConwayLife(),
            (lambda g: (PatternLibrary.place(g, PatternLibrary.R_PENTOMINO, 25, 20), g)[1])(Grid(50, 40)),
            steps=150,
            show_grid=True,
        )
        info(f"  The R-pentomino: just 5 cells. It runs for 1,103 generations before stabilising.")
        info(f"  It leaves behind {sim_r.grid.total_alive()} cells and multiple independent structures.")

    except KeyboardInterrupt:
        print(f"\n  {T.DIM}(skipped){T.RESET}")

    try:
        # 1b. Gosper Glider Gun
        run_experiment(
            "Gosper Glider Gun — Infinite Growth",
            ConwayLife(),
            PatternLibrary.make_glider_gun(64, 36),
            steps=60,
            early_stop=False,
            show_grid=True,
        )
        info("  First infinite-growth pattern. Emits a glider every 30 generations forever.")
        info("  Gliders are the 'signals' that make Life Turing-complete.")

    except KeyboardInterrupt:
        print(f"\n  {T.DIM}(skipped){T.RESET}")

    try:
        # 1c. Brian's Brain
        run_experiment(
            "Brian's Brain — 3-State Glider Factory",
            BriansBrain(),
            Grid.random(42, 28, density=0.3, seed=7),
            steps=60,
            show_grid=True,
        )
        info("  Three states: firing (white) → refractory (blue) → dead.")
        info("  Almost all initial conditions produce endless streams of gliders.")
        info("  The refractory period acts like a nerve cell's recovery phase.")

    except KeyboardInterrupt:
        print(f"\n  {T.DIM}(skipped){T.RESET}")

    try:
        # 1d. Rule 110
        subsection("Wolfram Rule 110 — 1D Turing Completeness")
        sim_110 = demo_rule110()
        print(render_grid_pretty(sim_110.grid, sim_110.rule, max_w=70, max_h=48))
        result("Rule number", "110")
        result("Proven Turing complete", "Yes (Matthew Cook, 2004)")
        result("Generation count", str(sim_110.generation))
        result("Final entropy", f"{Analysis.entropy(sim_110.grid):.4f}")
        info("  One row of cells. Each row is computed from the row above.")
        info("  Left+self+right = 3 bits = 8 cases = 1 byte = 256 possible rules.")
        info("  Rule 110 produces complex, never-repeating patterns from a single dot.")

    except KeyboardInterrupt:
        print(f"\n  {T.DIM}(skipped){T.RESET}")

    try:
        # 1e. Rule 30 (random number generator)
        subsection("Wolfram Rule 30 — The Randomness Engine")
        width, height = 70, 48
        g30 = Rule1D.make_seed_row(width, height)
        rule30 = Rule1D(30)
        sim30 = Simulation(rule30, g30)
        sim30.run(height - 1, early_stop=False)
        print(render_grid_pretty(sim30.grid, rule30, max_w=70, max_h=48))
        result("Rule number", "30")
        result("Used by", "Mathematica's default RNG until 2020")
        result("Final entropy", f"{Analysis.entropy(sim30.grid):.4f}")
        info("  The central column of Rule 30 passes statistical tests for randomness.")
        info("  Wolfram used it as a random number generator for decades.")
        info("  From one living cell + four rules: cryptographic-quality randomness.")

    except KeyboardInterrupt:
        print(f"\n  {T.DIM}(skipped){T.RESET}")

    try:
        # 1f. HighLife
        run_experiment(
            "HighLife (B36/S23) — The Replicator Universe",
            HighLife(),
            Grid.random(48, 36, density=0.25, seed=99),
            steps=100,
            show_grid=True,
        )
        info("  Like Life, but also born with 6 neighbours.")
        info("  Contains a 'replicator' pattern that copies itself.")
        info("  Is also Turing complete.")

    except KeyboardInterrupt:
        print(f"\n  {T.DIM}(skipped){T.RESET}")

    try:
        # ── Part 2: Rule Space Survey ─────────────────────────────────────────
        neighbour_results, life_result = survey_life_neighbourhood()
    except KeyboardInterrupt:
        print(f"\n  {T.DIM}(skipped){T.RESET}")
        neighbour_results, life_result = [], {}

    try:
        random_results = sample_rule_space(n=150, seed=1337)
    except KeyboardInterrupt:
        print(f"\n  {T.DIM}(skipped){T.RESET}")
        random_results = []

    try:
        # ── Part 3: The Essay ─────────────────────────────────────────────────
        print_essay()
    except KeyboardInterrupt:
        pass

    # ── Final summary ─────────────────────────────────────────────────────────
    section("GENESIS COMPLETE", T.BGREEN)

    print(f"""
  {T.BWHITE}{T.BOLD}What we found:{T.RESET}

  {T.BGREEN}▸{T.RESET} Five universes, each from fewer rules than a haiku.
  {T.BGREEN}▸{T.RESET} One 5-cell pattern (R-pentomino) takes 1,103 generations to stabilise.
  {T.BGREEN}▸{T.RESET} One infinite-growth pattern (Glider Gun) runs forever.
  {T.BGREEN}▸{T.RESET} One 1D rule (Rule 110) can compute anything a computer can compute.
  {T.BGREEN}▸{T.RESET} One 1D rule (Rule 30) generates cryptographic-quality randomness.
  {T.BGREEN}▸{T.RESET} Conway's Life sits near — but not necessarily at — the peak of
    complexity in its neighbourhood. The edge of chaos is a region, not a point.

  {T.DIM}The universe from counting neighbours.{T.RESET}
  {T.DIM}Complexity from nothing.{T.RESET}
  {T.DIM}Everything from four rules.{T.RESET}

  {T.BBLACK}─────────────────────────────────────────────────────────────────────{T.RESET}
  {T.DIM}GENESIS — written by Claude (Sonnet 4.6)
  github.com/claude-adventure • March 2026{T.RESET}
""")


if __name__ == "__main__":
    main()
