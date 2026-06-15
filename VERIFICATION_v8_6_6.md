# Verification v8.6.6 — real user flow and complex cases

## What was fixed after v8.6.5

1. Removed stale visible wording from the old wizard path, such as “Ответьте на 5 вопросов”.
2. Blocked transition to “Связи” until at least two participants are added.
3. Removed visible technology names from the initial stages. Before stack generation, the user sees only participants, interactions, and semantic clarifications.
4. Made stages visually sequential: participants, interactions, clarifications, stack, report. Earlier stages no longer keep all cards visible and mixed on screen.
5. Updated the real-user UI verification script to match the current participant → interaction → clarification → stack flow.

## Results

- `python run_tests.py`: 68/68 passed
- `pytest -q -rs`: 24 passed
- `python verify_action_grammar_matrix.py`: checked=2880, failures=0
- `python verify_full_stack_coverage.py`: channels=55, single=55, pairwise=3025, issues=0
- `python verify_semantic_question_stack_coverage.py`: semantic_options=55, channels=55, issues=0
- `python verify_branch_question_stack_flow.py`: branch_questions=60, channels=55, issues=0
- `python verify_complex_e2e_v860.py`: 5 complex cases, failed=0, covered 55/55 technologies
- `python verify_ui_real_user_path_v860.py`: 20 ok, 0 fail

## Real user flow tested

The test follows the current intended UX:

1. Open the constructor on mobile viewport.
2. Confirm there is no old wizard wording and no technology names before stack generation.
3. Confirm interaction stage is locked until participants exist.
4. Add participants: initiator, process service, external system, storage, analytics, manual review.
5. Add six interactions between participants.
6. Confirm technology names are still hidden before stack generation.
7. Open branch questions and answer semantic questions with buttons only.
8. Confirm technology names are still hidden at clarification stage.
9. Generate stack.
10. Confirm technologies and explanations appear after stack generation.
11. Open expert mode, manually override to RabbitMQ, reset auto stack.
12. Submit architecture check.
13. Validate payload: no missing systems, no self-dependencies, no invalid dependencies.
14. Confirm browser console has no errors.

## Complex cases tested

1. Digital banking product opening.
2. IoT telemetry and real-time alerts.
3. E-commerce order with catalog, ERP, partners, search and files.
4. Enterprise migration from legacy process.
5. Insurance claim with partners, documents, callbacks, legacy and DWH.

All complex cases analyzed successfully. Red verdicts are expected for intentionally risky production-level scenarios and represent risk findings, not crashes.
