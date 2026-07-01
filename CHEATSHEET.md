# OpenProfile — Cheat Sheet

Print this. Every command is typed into a terminal opened **in the project folder**.

## Which terminal (CLI) to use?

On this Windows machine, use **PowerShell** — it's the default Windows terminal and every
command below works in it as-is. (Git Bash or Command Prompt also work; only the
`setx` line at the bottom is Windows-specific.)

Open it in the right place: in File Explorer, go to the project folder, then either
- type `powershell` in the address bar and press Enter, **or**
- Shift + right-click in the folder → "Open PowerShell window here".

Check Python is available:

```
python --version        # expect Python 3.10 or newer
```

---

## The 3 commands you actually need

### 1. Safe offline demo (no internet) — use this on the projector
```
python examples/demo.py
```
Then open **examples/output/index.html** in your browser. Same result every time.

### 2. Profile a real business (uses the internet)
```
python -m openprofile "De Bortoli Wines" --state NSW --domain debortoli.com.au --html report.html --open
```
Opens a browser report automatically.

### 3. Quick answer in the terminal
```
python -m openprofile "Sunraysia Citrus Co" --state VIC
```

---

## Reading a command

```
python -m openprofile  "BUSINESS NAME"  --state VIC  --domain site.com.au  --html report.html  --open
|__ run the tool _____| |_ in quotes _| |_ state _|  |__ website ______|  |_ save report _|  |_ open it
```

## All options (all optional)

| Option | What it does |
|---|---|
| `--state NSW` | State hint (NSW, VIC, SA, QLD, WA, TAS, NT, ACT) — improves matching |
| `--domain example.com.au` | The business's website |
| `--html report.html` | Save a browser-viewable report |
| `--json out.json` | Save the raw data |
| `--open` | Auto-open the HTML report in your browser |
| `--offline` | Use only already-fetched data (no internet) |

## What the report shows

- **Entity** — legal name, ABN, status, type
- **Likelihood of currently trading** — a % and a label (Likely trading / Uncertain / Likely not trading)
- **Industry & sector (ANZSIC)** — classification, each with a confidence %
- **Provenance** — the sources behind every figure
- **Caveats** — the tool's own honest warnings

## Turn on official business-register (ABR) data — later

Works without this today. When your free ABN Lookup GUID arrives (~5 business days), run
once in PowerShell, then **open a new terminal**:

```
setx ABN_LOOKUP_GUID "your-guid-here"
```

After that, profiles automatically include official legal-name and trading-status data. No
code changes needed.

## If something looks off

- **"No module named openprofile"** → you're not in the project folder. `cd` into it first.
- **"Website not reachable: blocked by robots.txt"** → normal and correct: that site asked
  not to be crawled, so the tool didn't. Not an error.
- **Trading shows ~50% "Uncertain"** → little evidence was found (e.g. no website given).
  Add `--domain` to give it more to work with.
- **Run the tests** (proves everything works): `python -m pytest -q`
```
