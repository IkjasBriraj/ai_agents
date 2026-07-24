# Scope: E2E Testing Track

## Mission
Design and create a comprehensive, requirement-driven, opaque-box E2E test suite covering all 6 features across Tiers 1-4.
Publish `TEST_READY.md` upon completion.

## Requirements Reference
- Path to User Request: `d:\learning\code\ai_agents\.agents\orchestrator\ORIGINAL_REQUEST.md`
- Path to Test Infra Plan: `d:\learning\code\ai_agents\.agents\orchestrator\TEST_INFRA.md`
- Path to Global Architecture: `d:\learning\code\ai_agents\.agents\orchestrator\PROJECT.md`

## Features & Tiers
- **F1: Patch File Operation** (R1) - Tier 1 (5 tests), Tier 2 (5 boundary tests), Tier 3 (pairwise), Tier 4 (application scenario)
- **F2: AST Syntax Validation** (R1) - Tier 1 (5 tests), Tier 2 (5 boundary tests), Tier 3 (pairwise), Tier 4 (application scenario)
- **F3: Business Agent & CSV Tool** (R2) - Tier 1 (5 tests), Tier 2 (5 boundary tests), Tier 3 (pairwise), Tier 4 (application scenario)
- **F4: Routing & UI Selector** (R2) - Tier 1 (5 tests), Tier 2 (5 boundary tests), Tier 3 (pairwise), Tier 4 (application scenario)
- **F5: Voice Transcription Endpoint** (R3) - Tier 1 (5 tests), Tier 2 (5 boundary tests), Tier 3 (pairwise), Tier 4 (application scenario)
- **F6: Voice UI & Audio Encoder** (R3) - Tier 1 (5 tests), Tier 2 (5 boundary tests), Tier 3 (pairwise), Tier 4 (application scenario)

## Key Output
Create test file `backend/test_new_features.py` (or test runner) with all test cases, and generate `TEST_READY.md` at root and orchestrator folder.
