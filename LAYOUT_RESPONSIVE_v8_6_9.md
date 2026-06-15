# Проверка мобильной и адаптивной вёрстки v8.6.9

- OK: phone360 / participants_empty — overflow=0.0, overlaps=0, rects=4
- OK: phone360 / participants_filled — overflow=0.0, overlaps=0, rects=4
- OK: phone360 / interactions_empty — overflow=0.0, overlaps=0, rects=5
- OK: phone360 / interactions_filled — overflow=0.0, overlaps=0, rects=5
- OK: phone360 / clarifications — overflow=0.0, overlaps=0, rects=4
- OK: phone360 / stack_ready — overflow=0.0, overlaps=0, rects=7
- OK: phone390 / participants_empty — overflow=0.0, overlaps=0, rects=4
- OK: phone390 / participants_filled — overflow=0.0, overlaps=0, rects=4
- OK: phone390 / interactions_empty — overflow=0.0, overlaps=0, rects=5
- OK: phone390 / interactions_filled — overflow=0.0, overlaps=0, rects=5
- OK: phone390 / clarifications — overflow=0.0, overlaps=0, rects=4
- OK: phone390 / stack_ready — overflow=0.0, overlaps=0, rects=7
- OK: tablet768 / participants_empty — overflow=0.0, overlaps=0, rects=4
- OK: tablet768 / participants_filled — overflow=0.0, overlaps=0, rects=4
- OK: tablet768 / interactions_empty — overflow=0.0, overlaps=0, rects=5
- OK: tablet768 / interactions_filled — overflow=0.0, overlaps=0, rects=5
- OK: tablet768 / clarifications — overflow=0.0, overlaps=0, rects=4
- OK: tablet768 / stack_ready — overflow=0.0, overlaps=0, rects=7
- OK: desktop1366 / participants_empty — overflow=0.0, overlaps=0, rects=4
- OK: desktop1366 / participants_filled — overflow=0.0, overlaps=0, rects=4
- FAIL: desktop1366 / interactions_empty — overflow=0.0, overlaps=2, rects=5
- FAIL: desktop1366 / interactions_filled — overflow=0.0, overlaps=2, rects=5
- FAIL: desktop1366 / clarifications — overflow=0.0, overlaps=1, rects=4
- FAIL: desktop1366 / stack_ready — overflow=0.0, overlaps=2, rects=7

SUMMARY: 20 ok, 4 fail

FAILURES:
- ('desktop1366', 'interactions_empty', 'overlap', [('.guidebar', '.flow-stage-panel', 0.7), ('.guidebar', '.chain-preview', 0.26)])
- ('desktop1366', 'interactions_filled', 'overlap', [('.guidebar', '.flow-stage-panel', 0.69), ('.guidebar', '.chain-preview', 0.25)])
- ('desktop1366', 'clarifications', 'overlap', [('.guidebar', '.flow-stage-panel', 0.69)])
- ('desktop1366', 'stack_ready', 'overlap', [('.interactions-section', '.sticky-submit', 0.7), ('.chain-preview', '.sticky-submit', 0.26)])