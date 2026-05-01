# bQuant Compatibility

Living allowlist of libraries. For `bquant_snippets/`, use only `numpy`, `pandas`, and `matplotlib`. Status values: `allowed` / `blocked` / `untested`.

## Python

| Library     | Status    | Source            | Notes |
|-------------|-----------|-------------------|-------|
| numpy       | allowed   | assumed baseline  | |
| pandas      | allowed   | assumed baseline  | |
| statsmodels | untested  | not for snippets   | keep out of public paste snippets |
| matplotlib  | allowed   | assumed baseline  | |
| scipy       | untested  | —                 | confirm before using in a cell destined for bQuant |
| rpy2        | untested  | —                 | R bridge — needs supervisor confirmation; low confidence it's permitted |

## R (via `rpy2` or native bQuant kernel)

Open question. Confirm with supervisor whether R is available in bQuant and if so, which packages.

| Package | Status    | Source | Notes |
|---------|-----------|--------|-------|
| _TBD_   | untested  | —      | |

## How to use this doc

- **Before adding a new import** to a snippet that will be pasted into bQuant: check this table.
- **If the library is `untested`**: flag it in the snippet with a comment, run the cell in bQuant, and update the row to `allowed` or `blocked` with the source.
- **If the library is `blocked`**: find a Python-native alternative, or isolate the offending step to a cell we do not paste (e.g. pre-compute locally, paste only the result).
