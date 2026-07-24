# Project Execution Plan

## Objective
Implement advanced capabilities in local AI agents:
1. Incremental Code Modifiers (`patch` operation in `backend/agents/tools.py`, AST validation, CodeAgent prompt update).
2. Specialized Business Agent (`BusinessAgent` in `specialized_agents.py`, `csv_sheet_operation` in `tools.py`, permission check, routing rules in `orchestrator.py`, frontend selector in `MultiAgentHub.tsx`).
3. Voice Recording & Speech-to-Text (`SpeechRecognition` in `backend/requirements.txt`, `/agents/voice/transcribe` endpoint in `backend/agents/api.py`, browser PCM WAV encoder & mic button in `MultiAgentHub.tsx`, prompt auto-fill).
4. Comprehensive E2E Testing & Acceptance Gate + Adversarial Coverage Hardening.

## Topology & Orchestration Strategy
- **Dual Track Architecture**:
  - **Track 1: E2E Testing Track**: Requirements-driven, opaque-box test suite creation (Tiers 1-4). Outputs `TEST_READY.md`.
  - **Track 2: Implementation Track**:
    - **Milestone 1**: Incremental Code Modifiers (R1)
    - **Milestone 2**: Specialized Business Agent & CSV Tool (R2)
    - **Milestone 3**: Voice Recording & STT (R3)
    - **Milestone 4**: Final Milestone (Pass 100% E2E tests, Tier 5 Adversarial Coverage Hardening)

## Phasing & Milestones
- **Phase 1: Setup & Initialization**
  - Create orchestrator state & project documents (`PROJECT.md`, `TEST_INFRA.md`, `plan.md`, `context.md`, `progress.md`, `BRIEFING.md`, `ORIGINAL_REQUEST.md`).
  - Start liveness heartbeat cron (`schedule`).
- **Phase 2: Parallel Dispatch**
  - Spawn E2E Testing Orchestrator.
  - Spawn Sub-Orchestrator for M1 (R1 Patch Edits).
  - Spawn Sub-Orchestrator for M2 (R2 Business Agent).
  - Spawn Sub-Orchestrator for M3 (R3 Voice STT).
- **Phase 3: Integration & Final Milestone (M4)**
  - Monitor sub-orchestrators for completion.
  - Require M1, M2, M3 completion and `TEST_READY.md`.
  - Spawn Sub-Orchestrator for M4 to execute E2E Test Suite validation (Tiers 1-4) and Tier 5 Adversarial Coverage Hardening.
- **Phase 4: Forensic Audit & Gate Verification**
  - Invoke `teamwork_preview_auditor` for independent forensic verification.
  - Ensure zero integrity violations.
- **Phase 5: Final Report**
  - Report findings and outcomes to Sentinel.
