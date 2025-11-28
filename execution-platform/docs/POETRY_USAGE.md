# Poetry usage

Setup
- Install poetry: pipx install poetry (recommended) or pip install --user poetry
- cd ~/projects/maestro-platform/execution-platform
- poetry env use $(which python3)  # choose your Python 3.x
- poetry install

Run
- poetry run uvicorn execution_platform.gateway.app:app --reload --port 8080

Test
- poetry run pytest -q

Notes
- requirements.txt remains for legacy, but Poetry is the source of truth.
- Align package versions with maestro-templates; see docs/LIBRARY_ALIGNMENT.md.
- Optional: poetry install --with observability to include OTel packages.
