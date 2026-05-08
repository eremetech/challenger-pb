#!/usr/bin/env python3
"""Contextual bandit for the challenger skill.

Learns a linear reward model over 7 axes of challenge characterization.
Each axis value has a learned weight; a challenge's score is the sum of its
tag weights. Selection uses Thompson-style noise inversely proportional to
sample count to drive exploration of under-sampled values.
"""
import json
import math
import random
import sys
import time
from pathlib import Path

STATE_PATH = Path.home() / ".claude" / "skills" / "challenger" / "state.json"
LAST_PATH = Path.home() / ".claude" / "skills" / "challenger" / "last.json"

AXES = {
    "granularity": ["word", "claim", "argument", "frame", "purpose"],
    "direction":   ["inward", "outward", "lateral", "orthogonal", "temporal"],
    "distance":    ["adjacent", "reframe", "inversion"],
    "form":        ["question", "counterclaim", "analogy", "counterexample", "thought_experiment", "quiet_prompt"],
    "demand":      ["defend", "specify", "compare", "predict", "commit", "imagine"],
    "meta":        ["none", "process", "motivation", "pattern", "activity"],
    "register":    ["factual", "analytical", "analogical", "speculative", "imaginative"],
}

LEARNING_RATE = 0.25
EXPLORE_SCALE = 0.6


def fresh_state():
    return {
        "weights": {ax: {v: 0.0 for v in vs} for ax, vs in AXES.items()},
        "counts":  {ax: {v: 0 for v in vs} for ax, vs in AXES.items()},
        "tags":    {},
        "history": [],
    }


def load_state():
    if STATE_PATH.exists():
        state = json.loads(STATE_PATH.read_text())
        # backfill any newly added axis values
        for ax, vs in AXES.items():
            state["weights"].setdefault(ax, {})
            state["counts"].setdefault(ax, {})
            for v in vs:
                state["weights"][ax].setdefault(v, 0.0)
                state["counts"][ax].setdefault(v, 0)
        return state
    state = fresh_state()
    save_state(state)
    return state


def save_state(state):
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2))


def score_coords(state, coords):
    return sum(
        state["weights"].get(ax, {}).get(v, 0.0)
        for ax, v in coords.items()
    )


def uncertainty(state, coords):
    """Higher when tag values have been sampled less."""
    return sum(
        1.0 / math.sqrt(1 + state["counts"].get(ax, {}).get(v, 0))
        for ax, v in coords.items()
    )


def cmd_select(args):
    """Select one candidate from a JSON array and record it as last."""
    if not args:
        sys.exit("select requires a JSON array of candidates")
    candidates = json.loads(args[0])
    state = load_state()

    best = None
    best_noisy = -float("inf")
    for c in candidates:
        base = score_coords(state, c["axes"])
        unc = uncertainty(state, c["axes"])
        noisy = base + random.gauss(0.0, EXPLORE_SCALE) * unc / len(AXES)
        if noisy > best_noisy:
            best_noisy = noisy
            best = c

    for ax, v in best["axes"].items():
        if ax in state["counts"] and v in state["counts"][ax]:
            state["counts"][ax][v] += 1
    save_state(state)

    LAST_PATH.write_text(json.dumps({
        "challenge": best["text"],
        "axes": best["axes"],
        "timestamp": time.time(),
    }, indent=2))

    print(json.dumps(best))


def cmd_update(args):
    """Apply feedback (+1 hit / -1 miss) to the last presented challenge."""
    if not args:
        sys.exit("update requires +1 or -1")
    sign = int(args[0])
    if sign not in (1, -1):
        sys.exit("sign must be +1 or -1")
    tag = args[1].strip().lower() if len(args) > 1 and args[1].strip() else None

    if not LAST_PATH.exists():
        sys.exit("no last challenge recorded — nothing to update")
    last = json.loads(LAST_PATH.read_text())
    state = load_state()

    for ax, v in last["axes"].items():
        if ax in state["weights"] and v in state["weights"][ax]:
            state["weights"][ax][v] += LEARNING_RATE * sign

    if tag:
        entry = state["tags"].setdefault(tag, {
            "count": 0,
            "net": 0,
            "axes": {ax: {vv: 0 for vv in vs} for ax, vs in AXES.items()},
        })
        entry["count"] += 1
        entry["net"] += sign
        for ax, v in last["axes"].items():
            if ax in entry["axes"] and v in entry["axes"][ax]:
                entry["axes"][ax][v] += sign

    state["history"].append({
        "ts": time.time(),
        "sign": sign,
        "tag": tag,
        "axes": last["axes"],
        "challenge": last.get("challenge", ""),
    })
    save_state(state)

    print(f"updated ({sign:+d}){' tag=' + tag if tag else ''}")


def cmd_suggest_explore(args):
    """Return least-sampled value per axis."""
    state = load_state()
    out = []
    for ax, vs in AXES.items():
        counts = [(v, state["counts"][ax].get(v, 0)) for v in vs]
        counts.sort(key=lambda x: x[1])
        out.append({"axis": ax, "least_sampled": counts[0][0], "count": counts[0][1]})
    print(json.dumps(out, indent=2))


def cmd_stats(args):
    state = load_state()
    print("=== learned axis weights (higher = more often lands for you) ===")
    for ax, vs in state["weights"].items():
        ranked = sorted(vs.items(), key=lambda x: -x[1])
        print(f"  {ax:12s} " + "  ".join(f"{v}:{w:+.2f}" for v, w in ranked))
    print()
    print("=== sample counts ===")
    for ax, vs in state["counts"].items():
        total = sum(vs.values())
        print(f"  {ax:12s} n={total:<4d}  " + ", ".join(f"{v}:{c}" for v, c in vs.items()))
    if state["tags"]:
        print()
        print("=== tags (what lands for you, labeled) ===")
        for tag, info in sorted(state["tags"].items(), key=lambda x: -x[1]["count"]):
            top = []
            for ax, vs in info["axes"].items():
                best_v, best_c = max(vs.items(), key=lambda x: x[1])
                if best_c > 0:
                    top.append(f"{ax}:{best_v}")
            print(f"  {tag:20s} count={info['count']:<3d} net={info['net']:+d}  typical={', '.join(top)}")
    print()
    print(f"total feedback events: {len(state['history'])}")


def cmd_reset(args):
    save_state(fresh_state())
    if LAST_PATH.exists():
        LAST_PATH.unlink()
    print("state reset")


COMMANDS = {
    "select":          cmd_select,
    "update":          cmd_update,
    "suggest_explore": cmd_suggest_explore,
    "stats":           cmd_stats,
    "reset":           cmd_reset,
}


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        sys.exit(f"usage: bandit.py {{{'|'.join(COMMANDS)}}} [args]")
    COMMANDS[sys.argv[1]](sys.argv[2:])
