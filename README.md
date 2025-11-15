# Neuravia-Autonomy (Phase 1)

Ossature du projet : package Python, CLI minimale, tests Pytest basiques.

## Installation (dev)
```bash
pip install -U pip
pip install -e .[dev]
```

## Utilisation
```bash
python -m neuravia --help
python -m neuravia --goal "Hello" --dry-run --no-confirm
```

## Tests
```bash
pytest -q
```
