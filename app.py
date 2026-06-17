#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Интеграционный проектировщик v7.8 — сервер.

Запуск:  python app.py
Открыть: http://127.0.0.1:8110/
"""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import json
import os
import re
import sqlite3
import uuid
from urllib.parse import parse_qs, urlparse

from engine import analyze
from report import markdown_report
from learning import (
    evaluate_learning_solution, evaluate_reference, learning_result_html,
    list_cases, get_case, learning_catalog_summary, learning_hints,
    progress_for_learner, progress_markdown, save_learning_attempt,
    learning_attempt_markdown, validate_learning_catalog,
    interview_pack, reference_variants, build_learning_visual_payload,
)
import ui

HOST = os.environ.get('HOST', '0.0.0.0')
PORT = int(os.environ.get('PORT', '8110'))
BASE_PATH = os.environ.get('BASE_PATH', '').rstrip('/')
MAX_POST = int(os.environ.get('MAX_POST_BYTES', str(2 * 1024 * 1024)))
APP_DIR = Path(os.environ.get('APP_DIR', '.architect6'))
APP_DIR.mkdir(parents=True, exist_ok=True)
DB = APP_DIR / 'runs.sqlite3'

RUN_RE = re.compile(r'^/run/([0-9a-f]{32})(\.md)?$')
LEARNING_ATTEMPT_RE = re.compile(r'^/learning/attempt/([0-9a-f]{32})\.md$')
HEALTH_PATHS = {'/health', '/healthz', '/readyz', '/livez'}


def db():
    con = sqlite3.connect(DB)
    con.execute('CREATE TABLE IF NOT EXISTS runs '
                '(id TEXT PRIMARY KEY, created TEXT DEFAULT CURRENT_TIMESTAMP, '
                'payload TEXT, result TEXT)')
    return con


def save_run(payload, result):
    rid = uuid.uuid4().hex
    with db() as con:
        con.execute('INSERT INTO runs (id, payload, result) VALUES (?,?,?)',
                    (rid, json.dumps(payload, ensure_ascii=False),
                     json.dumps(result, ensure_ascii=False, default=str)))
    return rid


def load_run(rid):
    with db() as con:
        row = con.execute('SELECT result FROM runs WHERE id=?', (rid,)).fetchone()
    return json.loads(row[0]) if row else None


class Handler(BaseHTTPRequestHandler):
    server_version = 'Architect6'

    def _route_path(self):
        path = self.path.split('?', 1)[0]
        if BASE_PATH and path.startswith(BASE_PATH + '/'):
            path = path[len(BASE_PATH):]
        elif BASE_PATH and path == BASE_PATH:
            path = '/'
        return path

    def _query(self):
        return parse_qs(urlparse(self.path).query)

    def _send_head(self, code=200, ctype='text/plain; charset=utf-8'):
        self.send_response(code)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', '0')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()

    def _send(self, code, body, ctype='text/html; charset=utf-8'):
        data = body.encode('utf-8') if isinstance(body, str) else body
        self.send_response(code)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        self.wfile.write(data)

    def do_HEAD(self):
        path = self._route_path()

        if path in HEALTH_PATHS or path in ('/', '/index.html'):
            return self._send_head(200)

        if path in ('/invariants', '/invariants/', '/invariants.html'):
            return self._send_head(200)

        if path in ('/patterns', '/patterns/', '/patterns.html'):
            return self._send_head(200)

        if path in ('/learning', '/learning/', '/learning.html') or path.startswith('/learning/'):
            return self._send_head(200)

        m = RUN_RE.match(path)
        if m:
            res = load_run(m.group(1))
            return self._send_head(200 if res else 404)

        return self._send_head(404)

    def do_GET(self):
        path = self._route_path()
        if path in ('/', '/index.html'):
            return self._send(200, ui.form_page())
        if path in ('/invariants', '/invariants/', '/invariants.html'):
            return self._send(200, ui.invariant_reference_page())
        if path in ('/patterns', '/patterns/', '/patterns.html'):
            return self._send(200, ui.design_pattern_reference_page())
        if path in ('/learning', '/learning/', '/learning.html'):
            return self._send(200, ui.learning_home_page())
        m_attempt = LEARNING_ATTEMPT_RE.match(path)
        if m_attempt:
            md = learning_attempt_markdown(m_attempt.group(1))
            if md is None:
                return self._send(404, '# Учебная попытка не найдена\n', 'text/markdown; charset=utf-8')
            return self._send(200, md, 'text/markdown; charset=utf-8')
        if path.startswith('/learning/'):
            case_id = path.split('/', 2)[2].strip('/')
            return self._send(200, ui.learning_case_page(case_id))
        if path == '/api/learning/cases':
            return self._send(200, json.dumps({'ok': True, 'cases': list_cases(), 'catalog': learning_catalog_summary()}, ensure_ascii=False), 'application/json')
        if path == '/api/learning/catalog/validate':
            q = self._query()
            deep = (q.get('deep', ['0'])[0] in ('1', 'true', 'yes'))
            return self._send(200, json.dumps(validate_learning_catalog(deep=deep), ensure_ascii=False, default=str), 'application/json')
        if path == '/api/learning/hints':
            q = self._query()
            hint = learning_hints((q.get('case_id') or [''])[0], int((q.get('level') or ['1'])[0] or 1))
            return self._send(200, json.dumps(hint, ensure_ascii=False), 'application/json')
        if path == '/api/learning/interview':
            q = self._query()
            return self._send(200, json.dumps(interview_pack((q.get('case_id') or [''])[0]), ensure_ascii=False, default=str), 'application/json')
        if path == '/api/learning/reference':
            q = self._query()
            return self._send(200, json.dumps(reference_variants((q.get('case_id') or [''])[0]), ensure_ascii=False, default=str), 'application/json')
        if path == '/api/learning/visual-payload':
            q = self._query()
            controls = [x for x in (q.get('controls') or [''])[0].split(',') if x]
            built = build_learning_visual_payload((q.get('case_id') or [''])[0], controls, kind=(q.get('kind') or ['selected'])[0])
            return self._send(200, json.dumps(built, ensure_ascii=False, default=str), 'application/json')
        if path == '/api/learning/progress':
            q = self._query()
            learner_id = (q.get('learner_id') or ['anonymous'])[0]
            if (q.get('format') or ['json'])[0] == 'md':
                return self._send(200, progress_markdown(learner_id), 'text/markdown; charset=utf-8')
            return self._send(200, json.dumps(progress_for_learner(learner_id), ensure_ascii=False, default=str), 'application/json')
        if path in HEALTH_PATHS:
            return self._send(200, '{"ok":true}', 'application/json')
        m = RUN_RE.match(path)
        if m:
            res = load_run(m.group(1))
            if not res:
                return self._send(404, '<h1>Разбор не найден</h1>')
            if m.group(2):
                return self._send(200, markdown_report(res),
                                  'text/markdown; charset=utf-8')
            return self._send(200, ui.result_page(m.group(1), res))
        return self._send(404, '<h1>404</h1>')

    def do_POST(self):
        path = self._route_path()
        if path not in ('/api/analyze', '/api/learning/evaluate'):
            return self._send(404, '{"ok":false}', 'application/json')
        length = int(self.headers.get('Content-Length') or 0)
        if length > MAX_POST:
            return self._send(413, json.dumps(
                {'ok': False, 'errors': ['Слишком большой запрос.']}), 'application/json')
        try:
            payload = json.loads(self.rfile.read(length).decode('utf-8') or '{}')
        except (json.JSONDecodeError, UnicodeDecodeError):
            return self._send(400, json.dumps(
                {'ok': False, 'errors': ['Некорректный JSON.']}), 'application/json')
        if path == '/api/learning/evaluate':
            case_id = str(payload.get('case_id') or '')
            mode = str(payload.get('mode') or 'learning')
            learner_id = str(payload.get('learner_id') or 'anonymous')
            solution = payload.get('payload') or {}
            answer_text = str(payload.get('answer_text') or '')
            ev = evaluate_learning_solution(case_id, solution, mode=mode, answer_text=answer_text)
            if ev.get('ok'):
                attempt_id = save_learning_attempt(learner_id, case_id, solution, ev, mode=mode)
                ev['attempt_id'] = attempt_id
                ev['attempt_md_url'] = f'/learning/attempt/{attempt_id}.md'
                ev['html'] = learning_result_html(ev)
                # Не отдаём полный base_result в браузер: он тяжёлый, а markdown уже содержит полный разбор.
                ev.pop('base_result', None)
            return self._send(200, json.dumps(ev, ensure_ascii=False, default=str), 'application/json')
        res = analyze(payload)
        if not res['ok']:
            return self._send(200, json.dumps(res, ensure_ascii=False), 'application/json')
        rid = save_run(payload, res)
        return self._send(200, json.dumps({'ok': True, 'id': rid}), 'application/json')

    def log_message(self, fmt, *args):  # тихий лог
        pass


def main():
    srv = ThreadingHTTPServer((HOST, PORT), Handler)
    print(
        f'Интеграционный проектировщик: host={HOST} port={PORT}',
        flush=True,
    )
    srv.serve_forever()


if __name__ == '__main__':
    main()
