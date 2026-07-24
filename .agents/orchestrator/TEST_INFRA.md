# E2E Test Infra: Local AI Agents Enhancements

## Test Philosophy
- Opaque-box, requirement-driven E2E test suite.
- Derived directly from `ORIGINAL_REQUEST.md`.
- Methodologies: Category-Partition, Boundary Value Analysis, Pairwise Combinatorial Testing, Real-World Application Workloads.

## Feature Inventory
| # | Feature | Source (Requirement) | Tier 1 | Tier 2 | Tier 3 | Tier 4 |
|---|---------|---------------------|:------:|:------:|:------:|:------:|
| F1 | Patch File Operation | R1 | 5 | 5 | ✓ | ✓ |
| F2 | AST Validation on Patch | R1 | 5 | 5 | ✓ | ✓ |
| F3 | Business Agent & CSV Sheet Tool | R2 | 5 | 5 | ✓ | ✓ |
| F4 | Business Routing & UI Selector | R2 | 5 | 5 | ✓ | ✓ |
| F5 | Voice Transcription Endpoint | R3 | 5 | 5 | ✓ | ✓ |
| F6 | Voice Recorder & UI Integration | R3 | 5 | 5 | ✓ | ✓ |

## Test Architecture
- Backend Unit & Integration Tests: Pytest runner (`pytest backend/test_*.py` or new test file `backend/test_new_features.py`).
- Frontend Component / Integration Tests: Vitest / React testing or test scripts.
- E2E Test Suite Output: Publishes `TEST_READY.md` when created.

## Coverage Goals
- Tier 1: ≥5 per feature (30 tests)
- Tier 2: ≥5 per feature boundary (30 tests)
- Tier 3: Pairwise combinations across features (10 tests)
- Tier 4: Real-world application scenarios (5 tests)
- Total Minimum E2E Tests: ~75 test cases
