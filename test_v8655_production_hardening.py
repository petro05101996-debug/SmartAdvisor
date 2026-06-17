from copy import deepcopy

from engine import analyze
from learning import get_case


def test_stripped_bank_case_is_red_v8655():
    payload = deepcopy(get_case("bank-credit-bki-fraud")["payload"])
    for step in payload["steps"]:
        step["timeout_ms"] = ""
        step["retry"] = "none"
        step["idempotency"] = "none"
        step["compensation"] = ""
        step["failure_policy"] = ""
        step["data_in"] = ""
        step["data_out"] = ""
    res = analyze(payload)
    assert res["ok"] is True
    assert res["verdict"]["color"] == "red"
    assert res["verdict"]["score"] <= 5.0


def test_report_language_has_no_outbox_case_artifact_v8655():
    from report import humanize_terms
    text = "Сохранить решение и запись в таблица исходящих сообщений-таблицу"
    assert humanize_terms(text) == "Сохранить решение и запись в Outbox-таблицу"
