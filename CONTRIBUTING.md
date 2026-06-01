# Contributing — CRS Mismatch Detector

Thank you for contributing.

---

## Development Setup

### 1. Clone the repository

```bash
git clone https://github.com/vickyskarthik/QGIS-CRS-Mismatch.git
cd QGIS-CRS-Mismatch
```

### 2. Copy the plugin to your QGIS profile

```bash
cp -r plugin/crs_mismatch_detector \
  ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/
```

### 3. Install development dependencies

```bash
pip install flake8 black isort pytest pytest-qgis
```

### 4. Regenerate resources_rc.py

```bash
pyrcc5 crs_mismatch_detector/resources.qrc -o crs_mismatch_detector/resources_rc.py
```

---

## Code Standards

- Follow `CODING_STANDARDS.md` in `crs_mismatch_detector_claude_docs/`.
- Maximum line length: 100.
- 4-space indentation.
- `snake_case` for functions and variables; `PascalCase` for classes.
- No `processing` imports at module level — always lazy-import inside functions.
- Use `QgsSettings` — never `QSettings`.
- Always disconnect signals in `unload()`.
- Never modify original source layers.

---

## Running Lint

```bash
flake8 crs_mismatch_detector/ --max-line-length=100 --exclude=resources_rc.py
black --check crs_mismatch_detector/ --line-length 100 --exclude="resources_rc.py"
isort --check-only crs_mismatch_detector/ --skip resources_rc.py
```

---

## Running Tests

```bash
cd plugin
python -m pytest crs_mismatch_detector/test/ -v
```

Save test results to:

```
reports/test_results/
```

---

## Submitting Changes

1. Create a feature branch: `git checkout -b feature/my-feature`
2. Make your changes.
3. Run lint and tests.
4. Save test results under `reports/`.
5. Update `CHANGELOG.md`.
6. Open a pull request.

---

## Reporting Issues

Use the GitHub issue tracker:  
https://github.com/vickyskarthik/QGIS-CRS-Mismatch/issues

Include:
- QGIS version.
- Operating system.
- Steps to reproduce.
- Expected vs actual behaviour.
- Log messages from `View → Panels → Log Messages → CRS Mismatch Detector`.
