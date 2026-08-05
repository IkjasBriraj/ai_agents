# Implementation baseline

Recorded: 2026-07-31

## Current product scope

SeniorAgent is a local-first React and FastAPI application for running, configuring, evaluating, and scheduling AI agents. The UI currently exposes eleven sections: multi-agent hub, agent inspector, idea playground, hubs, workspace, schedules, arena, stats, builder, training, and settings.

## Verified baseline

- `npm run build` succeeds in `frontend`.
- `npm run lint` currently fails; this is tracked for Phase 5.
- Python source compilation succeeds.
- The test suite cannot run until `pytest` is installed in the selected Python environment.
- The frontend previously assumed a reachable backend and displayed raw network failures when it was unavailable.

## Phase 1 definition of done

- The UI visibly reports whether the backend, database, scheduler, and Ollama are ready.
- Backend and Ollama locations can be configured without source edits.
- The AI Guide does not auto-start while the app is in a limited or offline state.
- A local startup helper checks prerequisites and starts both application services.
