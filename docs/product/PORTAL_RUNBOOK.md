# ArchaeoAI portal runbook

This runbook operates the Phase 6C local synthetic demonstration. It does not enable live inference.

## 1. Install

From the repository root, create and activate a supported Python environment, then install the
optional portal dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[portal]"
```

## 2. Reset and seed the demo

```powershell
archaeoai portal --demo --reset
```

`--reset` replaces the ignored local demo database and adds three neutral synthetic projects. Do not
use it when existing local demo records must be retained.

## 3. Launch without resetting

```powershell
archaeoai portal --demo
```

The service binds only to `127.0.0.1` and reports its address in the terminal.

For Codex Web Preview only, explicitly bind the demonstration server to all container interfaces:

```powershell
archaeoai portal --demo --reset --host 0.0.0.0
```

Expose/open port `8000` in Web Preview. `0.0.0.0` is a listening address, not a browser URL. The
default remains `127.0.0.1`; `--host` rejects every other value.

## 4. Open the browser

Open:

`http://127.0.0.1:8000`

Enter the demo workspace, then create, authorize, and run a synthetic project. The approved model
status must remain `DISABLED / NOT AUTHORIZED`, and each synthetic result must report
`MODEL_EXECUTION: NOT_PERFORMED`.

## 5. Exercise the workflow

Use Projects to create or open a project, Results to filter synthetic hypotheses, Review to record a
human observation, Report to generate a print-ready summary, Audit to inspect events, and Settings to
change retention or delete the local project.

No screen should request real terrain, coordinates, model files, or archaeological identifiers.

## 6. Stop the service

Return to the terminal and press `Ctrl+C`.

## 7. Locate or delete local demo state

The database is:

`data/private/portal/archaeoai_portal.sqlite3`

The entire `data/private/` tree is ignored by Git. After stopping the service, the owner may delete
that SQLite file to remove all retained demo state. Running again with `--reset` also replaces it.

## Troubleshooting

- If the portal extra is missing, run `python -m pip install -e ".[portal]"`.
- If the port is occupied, use `archaeoai portal --demo --port 8001` and open the reported address.
- Ports below 1024 and non-local bind addresses are not supported.
- If approved-model mode is requested, the expected Phase 6C result is the controlled error
  `APPROVED_MODEL_RUNTIME_NOT_AUTHORIZED`.
