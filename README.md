# Challenger

A soft reinforcement learning environment for improving the quality of brainstorming and intellectual challenge.

Challenger is an AI agent environmnet that helps your agent act as a structured thinking partner. Instead of validating your reasoning, it productively resists it — surfacing hidden assumptions, reframing questions, and pushing for sharper thought. Over time, it learns which kinds of challenges actually land for you and adapts accordingly.

---

## How it works

Every time you reason out loud — planning a product, defending a decision, thinking through a problem — Challenger runs a generation-and-selection loop:

1. **Generates** three genuinely different candidate challenges against your reasoning.
2. **Tags** each candidate across 7 cognitive axes that characterize the nature and angle of the challenge.
3. **Selects** one using a contextual bandit that balances exploitation (what has worked before) with exploration (what hasn't been tried yet).
4. **Presents** only the winner — no meta-commentary, no hedging.
5. **Learns** from your feedback (`/challenger-hit` and `/challenger-miss`) by updating per-axis reward weights.

The result is a system that gets better at challenging *you specifically* — not in the abstract, but calibrated to your particular blind spots, reasoning patterns, and the kinds of pushback you actually find useful.

---

## The 7 axes

Each challenge is characterized along seven orthogonal dimensions:

| Axis | Values |
|---|---|
| **granularity** | `word` · `claim` · `argument` · `frame` · `purpose` |
| **direction** | `inward` · `outward` · `lateral` · `orthogonal` · `temporal` |
| **distance** | `adjacent` · `reframe` · `inversion` |
| **form** | `question` · `counterclaim` · `analogy` · `counterexample` · `thought_experiment` · `quiet_prompt` |
| **demand** | `defend` · `specify` · `compare` · `predict` · `commit` · `imagine` |
| **meta** | `none` · `process` · `motivation` · `pattern` · `activity` |
| **register** | `factual` · `analytical` · `analogical` · `speculative` · `imaginative` |

The combination of these coordinates defines the character of a challenge. A `frame / orthogonal / inversion / thought_experiment / imagine / none / speculative` challenge is a completely different cognitive move than `claim / inward / adjacent / question / defend / none / analytical`.

---

## The bandit

`bandit.py` implements a linear reward model over the axis space. Each axis value has a learned weight; a challenge's score is the sum of its tag weights. Selection uses Thompson-style noise inversely proportional to sample count — so under-explored axis values get a boost, ensuring the system systematically covers the space before settling into learned preferences.

Feedback updates are applied via gradient step (`LEARNING_RATE = 0.25`) to all axes of the presented challenge simultaneously. The history and tag memory allow inspection of which challenge archetypes have worked for a given user over time.

State is stored locally in `state.json`. Each new user starts with a flat prior — all weights zero, all counts zero — and the system personalizes from the first interaction.

---

## Files

```
SKILL.md       — agent skill definition (prompt + loop instructions for Cursor)
bandit.py      — selection, learning, and feedback CLI
state.json     — initial blank state (flat prior, ready for personalization)
```

---

## Slash commands

| Command | Effect |
|---|---|
| `/challenger-hit` | Mark the last challenge as useful — upweights its axis profile |
| `/challenger-miss` | Mark the last challenge as useless — downweights its axis profile |
| `/challenger-stats` | Print learned weights, sample counts, and tag memory |
| `/challenger-off` | Exit challenger mode, resume normal assistant behavior |

Optionally append a tag to `/challenger-hit` or `/challenger-miss` (e.g. `/challenger-miss made-up-argument`) to build a labeled history of challenge archetypes over time.

---

## Install

Copy the three files into `~/.claude/skills/challenger/` (or the equivalent skills directory for your AI assistant setup). The skill file follows the [Cursor Agent Skills](https://docs.cursor.com) format.

```bash
mkdir -p ~/.claude/skills/challenger
cp SKILL.md bandit.py state.json ~/.claude/skills/challenger/
```

Then invoke it from any conversation by activating the `challenger` skill.
