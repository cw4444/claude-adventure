# GENESIS — A Laboratory for Emergent Complexity

> *The universe from counting neighbours.*

A terminal program that explores how unbounded complexity arises from the
simplest possible rules, using cellular automata as a lens.

## The Question

Out of 262,144 possible outer-totalistic 2-state 8-neighbour cellular automata
rules, why does Conway's Life sit so close to the "edge of chaos"? What makes
it special?

## What It Does

- **Simulates 6 CA universes**: Conway's Life, Seeds, Brian's Brain, Wireworld,
  and two 1D Wolfram rules (110 and 30)
- **Famous patterns**: Gosper Glider Gun, R-pentomino, Diehard, Acorn
- **Complexity analysis**: Shannon entropy, spatial entropy, autocorrelation,
  temporal change — combined into a composite interestingness score
- **Rule space survey**: Evaluates all rules within Hamming distance 1 of Life
  and ranks them by complexity
- **Random sample**: Tests 150 random rules from the full rule space and
  classifies their behaviours
- **The Essay**: A meditation on emergence, Turing completeness, and the edge
  of chaos — written in the output itself

## Running It

```bash
python3 genesis.py
```

No dependencies. Pure Python 3.11 stdlib. Takes about 2 minutes to run the
full analysis.

## What It Found

From the rule space survey (March 2026 run):

| Rule | Complexity | Notes |
|------|------------|-------|
| B36/S23 (HighLife) | 0.767 | Has a replicator; also Turing complete |
| B37/S23 | 0.762 | Less studied |
| B3/S023 | 0.756 | Survival with 0 neighbours = sparsely immortal cells |
| **B3/S23 (Life)** | **0.700** | The classic |

Life is within the top complexity tier of its neighbourhood — a local maximum
by a 10% threshold. More importantly, in a random sample of 150 rules:

- **46.7%** are Chaotic (noise, no structure)
- **22.0%** are Frozen (static or trivially periodic)
- **10.0%** are Complex (the interesting zone Life lives in)
- **8.0%** are Extinct (population dies out)

Conway chose B3/S23 in 1970 specifically because it sat at the edge of chaos.
He found one of the ~12% of rules that produces persistent, complex behaviour —
but not just any one. He found one with *gliders* (signals) and *still lifes*
(memory), the two ingredients needed for computation.

## Why This Matters

Stephen Wolfram's Class IV cellular automata — the complex ones — are the only
class capable of universal computation. Wolfram's Rule 110 (1D) was proven
Turing complete by Matthew Cook in 2004. Conway's Life (2D) by Paul Rendell
in 2002. Both contain the same mathematical structure: enough order to preserve
information, enough chaos to propagate it.

This is the same structure found in:
- DNA (stable enough to inherit, mutable enough to evolve)
- Neural tissue (maintains criticality between ordered and chaotic firing)
- Markets (tradition vs. innovation)

The edge of chaos isn't a metaphor. It's a phase boundary, and life — biological
and computational — finds it.

---

*Written by Claude (Sonnet 4.6), March 2026.*

## License
This software is currently not licensed for commercial use. If you’d like to use this in a business setting or install it professionally, please contact me at cw4444@gmail.com
