# Project instructions

- This repository is a Python/FastAPI backend. The application and router registration live in `app/main.py`; add HTTP endpoints under `app/routes/`.
- Keep route handlers aligned with existing patterns and response shapes. Put domain behavior in `app/services/` and use the existing persistence patterns in `app/repositories/` and `app/services/`.
- Keep request/response data consistent with the models and schemas in `app/models/` and `app/schemas/`. Update affected tests when changing an API contract.
- Put operational and analytics scripts in `scripts/`. Before running a script or changing `.github/workflows/`, inspect its effects: the daily workflow updates results, processes feedback, generates predictions, and may write to external services or send Telegram messages.
- Treat `data/` and generated files as application data. Do not rewrite or regenerate them unless the task requires it.
- Read the relevant route, service, repository, and tests before changing behavior. Follow nearby code conventions rather than introducing a new framework or layer.
- Add or update tests in `tests/` for behavior changes. Tests use `unittest`; run the suite with `.venv/bin/python -m unittest discover -s tests -v`.
- CI configures Python 3.11 and installs dependencies from `requirements.txt`. Keep runtime dependency changes there and ensure compatibility with that Python version.
- Read credentials from the environment; do not print, commit, or replace secret values.
- Use `GUIA_RAPIDO.md` for current project commands and `INDEX.md` for navigation. Treat older analysis documents as historical; confirm claims against current code and workflows.
