"""
Society of Mind — blocks world demo (Minsky, 1986)

Minsky proposed that intelligence emerges from many simple agents,
each knowing only one small thing, interacting through shared state.

No single agent has the plan. No agent talks directly to another.
They read from and write to a shared world. The solution emerges.

Usage:
    python society_of_mind.py          # default puzzle
    python society_of_mind.py --hard   # harder initial state
"""

import sys
import time

# ANSI
GRN = '\033[92m'
YEL = '\033[93m'
CYN = '\033[96m'
DIM = '\033[2m'
RST = '\033[0m'
BLD = '\033[1m'

DELAY = 0.4


# ── Shared world state ────────────────────────────────────────────────────────
#
# All agents read from and write to this object.
# No agent calls another agent directly.

class World:
    def __init__(self, blocks, goal):
        self.blocks   = dict(blocks)   # block → location ('table' or block name)
        self.hand     = None           # what the hand is holding (None = empty)
        self.goal     = goal           # desired stack, bottom to top
        self.target   = None           # block an agent wants to move
        self.dest     = None           # where it should go
        self.done     = False

    def clear(self, block):
        """True if nothing is sitting on top of this block."""
        return not any(loc == block for b, loc in self.blocks.items())

    def render(self):
        """ASCII side-view of the current stack."""
        # find what's on what
        lines = []
        for block in reversed(self.goal):
            loc = self.blocks.get(block, '?')
            mark = GRN + '✓' + RST if loc == (
                'table' if block == self.goal[0]
                else self.goal[self.goal.index(block) - 1]
            ) else RED if False else ''
            lines.append(f"    [{block}] on {loc}")
        if self.hand:
            lines.append(f"    hand: holding [{self.hand}]")
        return '\n'.join(lines)


# ── Micro-agents ──────────────────────────────────────────────────────────────
#
# Each agent:
#   - checks one condition
#   - performs one action if the condition is met
#   - has no knowledge of the overall goal or other agents

def log(agent, msg, color=RST):
    print(f"  {DIM}[{agent:12s}]{RST} {color}{msg}{RST}")
    time.sleep(DELAY * 0.3)


def agent_see(w):
    """Survey the scene. Report which blocks are clear."""
    clear_blocks = [b for b in w.blocks if w.clear(b)]
    log("SEE", f"clear: {clear_blocks}", DIM)


def agent_find(w):
    """
    Scan the goal from bottom to top.
    Find the first block not yet in its correct position.
    Set w.target and w.dest so other agents know what to do.
    """
    for i, block in enumerate(w.goal):
        correct_loc = 'table' if i == 0 else w.goal[i - 1]
        if w.blocks.get(block) != correct_loc:
            w.target = block
            w.dest   = correct_loc
            log("FIND", f"'{block}' should be on '{correct_loc}', currently on '{w.blocks[block]}'", YEL)
            return
    # every block is where it belongs
    w.done = True
    log("FIND", "all blocks in position", GRN)


def agent_clear(w):
    """
    Cascade up through blockers until we find a block that can actually move.
    If B is on C is on A, and we want to move A, we climb the stack:
      A blocked by C → C blocked by B → B is clear → move B to table first.
    This is the emergent cascading behavior Minsky described: no single agent
    plans the whole sequence — the CLEAR agent just keeps asking "but what's
    in the way?" until it finds something it can act on.
    """
    if w.target is None or w.hand is not None:
        return

    current, dest = w.target, w.dest
    redirected = False

    while True:
        if not w.clear(current):
            blocker = next(b for b, loc in w.blocks.items() if loc == current)
            log("CLEAR", f"'{current}' blocked by '{blocker}' — go up", YEL)
            current, dest = blocker, 'table'
            redirected = True
        elif dest != 'table' and not w.clear(dest):
            blocker = next(b for b, loc in w.blocks.items() if loc == dest)
            log("CLEAR", f"destination '{dest}' blocked by '{blocker}' — go up", YEL)
            current, dest = blocker, 'table'
            redirected = True
        else:
            break

    w.target, w.dest = current, dest
    if redirected:
        log("CLEAR", f"will move '{current}' to '{dest}' first", YEL)
    else:
        log("CLEAR", f"'{current}' and '{dest}' both clear", DIM)


def agent_grasp(w):
    """Pick up the target block if the hand is empty and the block is clear."""
    if w.hand is not None or w.target is None:
        return
    if w.clear(w.target):
        w.hand = w.target
        w.blocks[w.target] = 'in-hand'
        log("GRASP", f"picked up '{w.hand}'", CYN)


def agent_move(w):
    """
    Place the held block at its destination, if the destination is clear
    (or is the table, which is always available).
    """
    if w.hand is None or w.dest is None:
        return
    dest_clear = (w.dest == 'table') or w.clear(w.dest)
    if dest_clear:
        w.blocks[w.hand] = w.dest
        log("MOVE", f"placed '{w.hand}' on '{w.dest}'", CYN)
        w.hand   = None
        w.target = None
        w.dest   = None


def agent_check(w):
    """Print the current state of the world."""
    state = '  '.join(f"{b}→{loc}" for b, loc in sorted(w.blocks.items()))
    log("CHECK", state, DIM)


AGENTS = [agent_see, agent_find, agent_clear, agent_grasp, agent_move, agent_check]


# ── Run ───────────────────────────────────────────────────────────────────────

def run(blocks, goal, max_rounds=15):
    w = World(blocks, goal)

    print(f"\n{BLD}Goal:{RST} stack {goal} (left = bottom, right = top)")
    print(f"{BLD}Start:{RST} {dict(blocks)}\n")
    print("Each agent knows only one thing. No agent has the full plan.")
    print("Watch what emerges.\n")
    print("=" * 60)

    for round_num in range(1, max_rounds + 1):
        print(f"\n{BLD}Round {round_num}{RST}")
        for agent in AGENTS:
            agent(w)
            if w.done:
                break
        time.sleep(DELAY)
        if w.done:
            break

    print("\n" + "=" * 60)
    if w.done:
        print(f"\n{GRN}{BLD}Done.{RST} Tower built.\n")
        # draw the tower
        print("  Final stack (top to bottom):")
        for block in reversed(goal):
            print(f"    [{block}]")
        print("   -----")
    else:
        print(f"\nDid not complete in {max_rounds} rounds.")


# ── Puzzles ───────────────────────────────────────────────────────────────────

EASY = {
    'start':  {'A': 'table', 'B': 'table', 'C': 'A'},   # C sitting on A, B free
    'goal':   ['A', 'B', 'C'],                            # want A→B→C bottom to top
    'note':   "C blocks A. Must move C first, then build B→A, C→B.",
}

HARD = {
    # B is on C is on A. Need to reverse to A→B→C.
    'start':  {'A': 'table', 'C': 'A', 'B': 'C'},
    'goal':   ['A', 'B', 'C'],
    'note':   "Fully reversed stack. Three moves, each blocked by the previous.",
}

puzzle = HARD if '--hard' in sys.argv else EASY

print(f"\n{BLD}Society of Mind — Blocks World{RST}")
print(f"{BLD}Minsky, 1986{RST}\n")
print(f"Puzzle: {puzzle['note']}")

run(puzzle['start'], puzzle['goal'])
