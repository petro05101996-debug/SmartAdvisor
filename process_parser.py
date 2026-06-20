# Детерминированный парсер компактного описания процесса.
# Формат (свободный, человеко-читаемый), одна строка = один шаг:
#   действие | система | канал | флаги
# Примеры строк:
#   принять заказ | API | rest | пишет
#   списать оплату | PaymentGW(внешняя,нестабильная) | rest | блокирует, retry:auto
#   опубликовать событие | Kafka | kafka
#   сохранить статус | DB | db | пишет, идемпотентность:key
#
# Шапка (опционально), строки до первого шага:
#   процесс: Оплата заказа
#   сущность: Order
#   деньги: direct
#   клиенту: да
#   регуляторика: да
#   sla: 2000
#   нагрузка: 300 x4
#
# Парсер чисто на правилах — никакой модели. Распознаёт:
#  - канал по ключевым словам,
#  - флаги (пишет/блокирует/retry/идемпотентность/таймаут),
#  - роль и стабильность системы из скобок,
#  - зависимости по умолчанию (от предыдущего шага), или явно "<-N".
import re

CHANNELS = {"rest","grpc","soap","graphql","kafka","rabbitmq","queue","event","db","file","batch"}
CHANNEL_HINTS = {
    "http":"rest","апи":"rest","api":"rest","рест":"rest",
    "кафка":"kafka","kafka":"kafka","событ":"event","event":"event",
    "очеред":"queue","queue":"queue","rabbit":"rabbitmq","кролик":"rabbitmq",
    "баз":"db","db":"db","sql":"db","субд":"db","файл":"file","file":"file","батч":"batch","batch":"batch",
    "grpc":"grpc","soap":"soap","graphql":"graphql",
}
ROLE_HINTS = {
    "внешн":"external","external":"external","партнер":"external","партнёр":"external",
    "брокер":"broker","broker":"broker","очеред":"broker",
    "баз":"db","db":"db","субд":"db","хранил":"db",
    "легаси":"legacy","legacy":"legacy","устар":"legacy",
    "аналитик":"analytics","analytics":"analytics","dwh":"analytics","дх":"analytics",
}
STAB_HINTS = {"нестабильн":"unstable","unstable":"unstable","огранич":"limited","limited":"limited","стабильн":"stable","stable":"stable"}

def _norm(s): return (s or "").strip()

def parse_meta_line(line, meta):
    low = line.lower()
    m = re.match(r"(процесс|сущность|деньги|клиенту|регуляторик\w*|regulatory|sla|нагрузк\w*|цель|порядок|статус\w*|statuses|ключи|lookup_keys|lookup|поля|fields)\s*[:=]\s*(.+)", low)
    if not m: return False
    key, val = m.group(1), _norm(m.group(2))
    if key.startswith("процесс"): meta["name"]=val.capitalize()
    elif key.startswith("сущн"): meta["entity"]=val.strip().title() if val.islower() else val.strip()
    elif key.startswith("деньг"):
        # Важно: indirect содержит подстроку direct. Проверяем точные токены и indirect раньше direct.
        tokens = set(re.findall(r"[a-zа-яё]+", val.lower()))
        if "indirect" in tokens or "косвенно" in tokens or "косвенный" in tokens or "косв" in val:
            meta["money"] = "indirect"
        elif "direct" in tokens or "прямой" in tokens or "прямые" in tokens or "прям" in val:
            meta["money"] = "direct"
        else:
            meta["money"] = "no"
    elif key.startswith("клиент"): meta["customer_visible"]="да" if val in ("да","yes","y","true") else "no"
    elif key.startswith("регулятор") or key == "regulatory": meta["regulatory"]= val in ("да","yes","y","true")
    elif key=="sla":
        d=re.search(r"\d+",val); meta["sla_ms"]=int(d.group()) if d else 0
    elif key.startswith("нагрузк"):
        nums=re.findall(r"\d+",val); meta["load_rps"]=int(nums[0]) if nums else 0; meta["peak_factor"]=int(nums[1]) if len(nums)>1 else 1
    elif key.startswith("цель"): meta["goal"]=val
    elif key.startswith("порядок"): meta["ordering"]= "global" if "глобал" in val else ("per_entity" if "сущност" in val or "per_entity" in val or "entity" in val else "no")
    elif key.startswith("статус") or key == "statuses": meta["statuses"] = val
    elif key.startswith("ключ") or key in ("lookup", "lookup_keys"): meta["lookup_keys"] = val
    elif key.startswith("пол") or key == "fields": meta["fields"] = val
    return True

def detect_channel(text):
    low=text.lower()
    for word in re.findall(r"[a-zа-яё]+", low):
        if word in CHANNELS: return word
    for hint,ch in CHANNEL_HINTS.items():
        if hint in low: return ch
    return "rest"

def parse_system(raw):
    # "PaymentGW(внешняя,нестабильная)" -> name + role + stability
    m=re.match(r"([^(]+)(?:\(([^)]*)\))?", raw.strip())
    name=_norm(m.group(1)); attrs=(m.group(2) or "").lower()
    role="internal"; stab="unknown"; crit="medium"
    for hint,r in ROLE_HINTS.items():
        if hint in attrs: role=r; break
    for hint,s in STAB_HINTS.items():
        if hint in attrs: stab=s; break
    if "критич" in attrs or "critical" in attrs: crit="high"
    return name, role, stab, crit

def parse_flags(raw, channel):
    low=raw.lower()
    flags={"blocking": None,"writes_entity":False,"retry":"none","idempotency":"none","timeout_ms":0}
    if "пишет" in low or "запис" in low or "write" in low: flags["writes_entity"]=True
    if "блок" in low or "ждем" in low or "ждём" in low or "block" in low: flags["blocking"]=True
    if "неблок" in low or "async" in low or "асинхрон" in low or "non-block" in low: flags["blocking"]=False
    rm=re.search(r"retry\s*[:=]?\s*(auto|manual|авто|ручн)", low) or re.search(r"(повтор\w*\s*авто|авторетрай)", low)
    if rm: flags["retry"]="auto" if ("auto" in rm.group(0) or "авто" in rm.group(0)) else "manual"
    im=re.search(r"идемпотент\w*\s*[:=]?\s*(key|natural|ключ|натур)", low) or re.search(r"idempoten\w*\s*[:=]?\s*(key|natural)", low)
    if im: flags["idempotency"]="key" if ("key" in im.group(0) or "ключ" in im.group(0)) else "natural"
    elif "идемпотент" in low or "idempoten" in low: flags["idempotency"]="key"
    tm=re.search(r"(?:таймаут|timeout)\s*[:=]?\s*(\d+)", low)
    if tm: flags["timeout_ms"]=int(tm.group(1))
    # default blocking by channel if not specified
    if flags["blocking"] is None:
        flags["blocking"]= channel in ("rest","grpc","soap","graphql")
    return flags

def parse_dep(raw, order):
    m=re.search(r"<-?\s*(\d+)", raw) or re.search(r"(?:от|after|depends)\s*(\d+)", raw.lower())
    return int(m.group(1)) if m else (order-1 if order>1 else 0)


def has_explicit_dep(raw):
    return bool(re.search(r"<-?\s*\d+", raw or "") or re.search(r"(?:от|after|depends)\s*\d+", (raw or "").lower()))

def parse_process(text):
    payload={"meta":{},"systems":[],"steps":[]}
    sys_seen={}
    order=0
    for line in text.splitlines():
        line=line.strip()
        if not line or line.startswith("#"): continue
        if "|" not in line and parse_meta_line(line, payload["meta"]): continue
        # это шаг
        parts=[p.strip() for p in line.split("|")]
        action=parts[0]
        sys_raw=parts[1] if len(parts)>1 else "—"
        name, role, stab, crit = parse_system(sys_raw)
        # канал: явный во 2-3 позиции или угадать
        channel=None
        for p in parts[2:]:
            cand=detect_channel(p)
            if any(w in p.lower() for w in list(CHANNELS)+list(CHANNEL_HINTS)): channel=cand; break
        if channel is None: channel=detect_channel(action+" "+sys_raw)
        flagstr=" ".join(parts[2:])
        flags=parse_flags(flagstr, channel)
        order+=1
        if name not in sys_seen and name!="—":
            payload["systems"].append({"name":name,"role":role,"stability":stab,"criticality":crit})
            sys_seen[name]=True
        step={"order":order,"name":action,"system":name,"channel":channel,
              "depends_on":parse_dep(flagstr, order), **flags}
        payload["steps"].append(step)
    return payload

if __name__=="__main__":
    sample="""процесс: Оплата заказа
сущность: Order
деньги: direct
клиенту: да
sla: 2000
принять заказ | API | rest | пишет
списать оплату | PaymentGW(внешняя, нестабильная) | rest | блокирует
сохранить статус | DB(база) | db | пишет, идемпотентность:key
отправить в аналитику | Analytics(аналитика) | rest | блокирует"""
    import json
    p=parse_process(sample)
    print(json.dumps(p, ensure_ascii=False, indent=2))


# ---------------------------------------------------------------------------
# v8.6.68: маршруты from→to и безопасный разбор свободного текста.
# Старый компактный формат "действие | система | канал | флаги" оставлен,
# но теперь поддерживается формат "действие | источник -> получатель | канал | флаги".
# Если source/target не указаны, они выводятся из предыдущего шага, чтобы отчёт
# больше не строил бессмысленные связи вида System → System.
_ROUTE_RE = re.compile(r"\s*(.+?)\s*(?:->|→|=>|↦|\s+к\s+|\s+в\s+|\s+во\s+)\s*(.+?)\s*$", re.I)

ROLE_BY_NAME_HINTS = {
    "kafka": "broker", "кафка": "broker", "rabbit": "broker", "queue": "broker", "очеред": "broker",
    "db": "db", "бд": "db", "база": "db", "mapping": "db", "мапп": "db", "inbox": "db",
    "dwh": "analytics", "витрин": "analytics", "аналит": "analytics", "data warehouse": "analytics",
    "ук": "external", "партнер": "external", "партнёр": "external", "provider": "external",
}

def _role_by_name(name, default="internal"):
    low = (name or "").lower()
    for hint, role in ROLE_BY_NAME_HINTS.items():
        if hint in low:
            return role
    return default


def _ensure_system(payload, seen, name, role="internal", stability="unknown", criticality="medium"):
    name = _norm(name)
    if not name or name == "—" or name in seen:
        return
    payload["systems"].append({"name": name, "role": role or _role_by_name(name), "stability": stability, "criticality": criticality})
    seen[name] = True




def _executor_for_route(action, source, target, channel):
    low = (action or '').lower()
    # Получение/чтение/приём выполняет получатель. Сохранение/маппинг/валидация выполняет сервис-источник, даже если объект «входящий».
    if any(x in low for x in ['сохран', 'запис', 'фиксир', 'сопостав', 'мапп', 'обогат', 'валид', 'провер', 'обнов']):
        return source
    if any(x in low for x in ['получ', 'приня', 'читать', 'прочит', 'consume', 'консьюм', 'обработать вход', 'входящ']):
        return target
    if channel == 'db':
        return source
    if channel in ('kafka', 'rabbitmq', 'queue', 'event') and any(x in low for x in ['прочит', 'consume', 'получ']):
        return target
    return source or target

def _parse_route(sys_raw, prev_target=""):
    raw = _norm(sys_raw)
    m = _ROUTE_RE.match(raw)
    if m and not any(x in raw.lower() for x in ["http://", "https://"]):
        return _norm(m.group(1)), _norm(m.group(2))
    # Старый формат: указана только система шага. Источник выводим из предыдущего шага.
    return (_norm(prev_target) or "Инициатор"), raw


def _natural_sentences(text):
    # Дробим не только по точкам, но и по запятым перед новым действием, чтобы
    # обычный абзац "УК отправляет..., банк сохраняет..., публикует..." давал цепочку.
    text = re.sub(r"\s+", " ", text.strip())
    text = re.sub(r",\s+(?=(?:банк|сервис|система|ук|он|она|далее|затем|после этого)\b)", ". ", text, flags=re.I)
    return [x.strip(" .;—-") for x in re.split(r"[.!?;\n]+", text) if x.strip(" .;—-")]




def _clean_target_phrase(target):
    t = _norm(target)
    low = t.lower()
    # Сохраняем явно многосоставные получатели.
    if any(x in low for x in ("ресурс", "dwh", "аналит", "kafka", "кафка", "mapping", "db", "бд")):
        return t
    # Частая конструкция: "в банк статусы операций" — получатель "банк", остальное объект данных.
    for known in ("банк", "ук", "api", "сервис", "шина", "брокер"):
        if low == known or low.startswith(known + " "):
            return t.split()[0] if known not in ("api",) else t.split()[0].upper()
    words = t.split()
    if len(words) > 3:
        return " ".join(words[:2])
    return t

def _natural_step_from_clause(clause, order, prev_actor="", prev_target=""):
    low = clause.lower()
    actor = ""
    target = ""
    action = clause[0].upper() + clause[1:] if clause else f"Шаг {order}"
    channel = detect_channel(clause)
    writes = any(w in low for w in ["сохраня", "записыва", "обновля", "клад", "фиксиру"])
    # X отправляет/передаёт/публикует ... в Y
    m = re.search(r"^(?P<actor>[A-ZА-ЯЁa-zа-яё0-9_ -]{2,40}?)\s+(?:отправляет|переда[её]т|публикует|клад[её]т|посылает|высылает|направляет|пишет)\b.*?\s(?:в|во|к|на)\s+(?P<target>[A-ZА-ЯЁa-zа-яё0-9_ /-]{2,60})$", clause, re.I)
    if m:
        actor, target = _norm(m.group('actor')), _clean_target_phrase(m.group('target'))
    else:
        m = re.search(r"^(?P<actor>[A-ZА-ЯЁa-zа-яё0-9_ -]{2,40}?)\s+(?:сохраняет|записывает|фиксирует)\b", clause, re.I)
        if m:
            actor = _norm(m.group('actor'))
            target = f"{actor} DB"
            channel = "db"
            writes = True
        else:
            m = re.search(r"^(?P<actor>[A-ZА-ЯЁa-zа-яё0-9_ -]{2,40}?)\s+(?:сопоставляет|маппит|ищет|обогащает)\b", clause, re.I)
            if m:
                actor = _norm(m.group('actor'))
                target = "Mapping DB"
                channel = "db"
            else:
                actor = prev_actor or prev_target or "Сервис процесса"
                # Если в тексте явно есть Kafka/DWH/ресурсные системы, используем их как получателя.
                if re.search(r"\bkafka\b|кафк", low): target, channel = "Kafka", "kafka"
                elif re.search(r"\bdwh\b|аналит|витрин", low): target, channel = "DWH", "batch"
                elif "ресурс" in low: target, channel = "Ресурсные системы", "kafka"
                else: target = actor
    # Множественные получатели типа "ресурсные системы и DWH" здесь не размножаем,
    # но сохраняем читаемый target; компактный формат позволяет разнести их явно.
    if "ресурс" in low and "dwh" in low and "Kafka" not in target:
        target = "Ресурсные системы и DWH"
        if channel == "rest": channel = "kafka"
    if "kafka" in low or "кафк" in low:
        target, channel = "Kafka", "kafka"
    flags = parse_flags(clause, channel)
    flags["writes_entity"] = flags.get("writes_entity") or writes
    if flags["blocking"] is None:
        flags["blocking"] = channel in ("rest", "grpc", "soap", "graphql", "db")
    return {
        "order": order,
        "name": action,
        "system": actor or target,
        "source_system": actor or prev_target or "Инициатор",
        "target_system": target or actor,
        "channel": channel,
        "depends_on": order - 1 if order > 1 else 0,
        **flags,
    }


# Сохраняем старую функцию на случай отладки.
_PARSE_PROCESS_LEGACY = parse_process

def parse_process(text):
    payload = {"meta": {}, "systems": [], "steps": []}
    sys_seen = {}
    order = 0
    prev_target = ""
    prev_actor = ""
    raw_lines = [ln.strip() for ln in text.splitlines() if ln.strip() and not ln.strip().startswith("#")]
    pipe_lines = [ln for ln in raw_lines if "|" in ln]
    # meta из любых строк до/между шагами
    for ln in raw_lines:
        if "|" not in ln:
            parse_meta_line(ln, payload["meta"])
    if pipe_lines:
        last_inbound_by_target = {}
        broker_like = {"broker"}
        for line in raw_lines:
            if not line or line.startswith("#"):
                continue
            if parse_meta_line(line, payload["meta"]):
                continue
            if "|" not in line:
                continue
            parts = [p.strip() for p in line.split("|")]
            action = parts[0]
            sys_raw = parts[1] if len(parts) > 1 else "—"
            source, target = _parse_route(sys_raw, prev_target)
            channel = None
            for p in parts[2:]:
                cand = detect_channel(p)
                if any(w in p.lower() for w in list(CHANNELS) + list(CHANNEL_HINTS)):
                    channel = cand
                    break
            if channel is None:
                channel = detect_channel(action + " " + sys_raw)
            # executor/system: для старого формата оставляем указанную систему; для route — выводим из действия.
            has_route = ("->" in sys_raw or "→" in sys_raw or "=>" in sys_raw or "↦" in sys_raw)
            sys_name = _executor_for_route(action, source, target, channel) if has_route else target
            base_name, role, stab, crit = parse_system(sys_name)
            target_name, target_role, target_stab, target_crit = parse_system(target)
            source_name, source_role, source_stab, source_crit = parse_system(source)
            flagstr = " ".join(parts[2:])
            # Флаги можно писать как в отдельной колонке, так и прямо в названии шага.
            flags = parse_flags(flagstr + " " + action, channel)
            order += 1
            _ensure_system(payload, sys_seen, source_name, source_role or _role_by_name(source_name), source_stab, source_crit)
            _ensure_system(payload, sys_seen, target_name, target_role or _role_by_name(target_name), target_stab, target_crit)
            _ensure_system(payload, sys_seen, base_name, role or _role_by_name(base_name), stab, crit)
            dep = parse_dep(flagstr, order)
            if not has_explicit_dep(flagstr):
                # Для fan-out из брокера несколько consumers не должны зависеть друг от друга.
                # Если источник текущего шага ранее был target producer-а (Bank -> Kafka, затем Kafka -> C1/C2/DWH),
                # все такие consumer-шаги зависят от producer-шага, а не от предыдущего consumer-а.
                if _role_by_name(source_name) in broker_like and source_name in last_inbound_by_target:
                    dep = last_inbound_by_target[source_name]
            step = {"order": order, "name": action, "system": base_name, "source_system": source_name,
                    "target_system": target_name, "producer": source_name, "consumer": target_name,
                    "channel": channel, "depends_on": dep, **flags}
            payload["steps"].append(step)
            if target_name:
                last_inbound_by_target[target_name] = order
            prev_target = target_name or base_name
            prev_actor = base_name
    else:
        # Лучшее усилие для обычного абзаца. Это не LLM: если уверенность низкая,
        # ядро дальше снизит score и попросит подтвердить карту процесса.
        body_lines = []
        for ln in raw_lines:
            if not parse_meta_line(ln, payload["meta"]):
                body_lines.append(ln)
        for clause in _natural_sentences("\n".join(body_lines)):
            if parse_meta_line(clause, payload["meta"]):
                continue
            order += 1
            step = _natural_step_from_clause(clause, order, prev_actor, prev_target)
            payload["steps"].append(step)
            for nm in (step.get("source_system"), step.get("target_system"), step.get("system")):
                _ensure_system(payload, sys_seen, nm, _role_by_name(nm), "unknown", "medium")
            prev_actor = step.get("system") or prev_actor
            prev_target = step.get("target_system") or prev_target
        payload["meta"]["parser_mode"] = "natural_text_best_effort"
        payload["meta"]["parser_warning"] = "Свободный текст разобран эвристически. Перед финальным отчётом подтвердите карту процесса."
    return payload

# ---------------------------------------------------------------------------
# v8.6.71: compact-text parser keeps engineering controls from flag columns.
# The previous parser correctly built routes, but flags like "DLQ, replay,
# reconciliation, audit journal, event envelope" were not copied to the step
# fields that the deterministic engine checks. This wrapper preserves them.
_PARSE_PROCESS_V8671 = parse_process

def _v8671_is_meta_line(line):
    tmp = {}
    return parse_meta_line(line, tmp)

def _v8671_normalize_fields(raw):
    raw = _norm(raw)
    if not raw:
        return raw
    # Human shorthand: поля: eventId|eventType|eventVersion|occurredAt|operationId
    # Engine format: eventId:string|required, eventType:string|required, ...
    if ',' not in raw and '|' in raw and ':' not in raw:
        names = [x.strip() for x in raw.split('|') if x.strip()]
        return ', '.join(f'{n}:string|required' for n in names)
    return raw

_EXTRA_META_RE_V8671 = re.compile(r'(ограничен\w*|constraints|контрол\w*|эксплуатац\w*|наблюдаем\w*|audit|аудит|reconciliation|сверк\w*)\s*[:=]\s*(.+)', re.I)

def parse_process(text):
    payload = _PARSE_PROCESS_V8671(text)
    meta = payload.setdefault('meta', {})
    if meta.get('fields'):
        meta['fields'] = _v8671_normalize_fields(meta.get('fields'))
    extras = []
    pipe_steps = []
    for line in [ln.strip() for ln in text.splitlines() if ln.strip() and not ln.strip().startswith('#')]:
        m = _EXTRA_META_RE_V8671.match(line)
        if m:
            extras.append(m.group(2).strip())
            continue
        if '|' in line and not _v8671_is_meta_line(line):
            pipe_steps.append(line)
    if extras:
        old = meta.get('constraints') or ''
        meta['constraints'] = (old + '; ' + '; '.join(extras)).strip('; ')
    fields_text = meta.get('fields') or ''
    for idx, line in enumerate(pipe_steps):
        if idx >= len(payload.get('steps') or []):
            break
        parts = [p.strip() for p in line.split('|')]
        flagstr = ' '.join(parts[2:]).strip()
        step = payload['steps'][idx]
        if flagstr:
            step['compensation'] = (str(step.get('compensation') or '') + ' ' + flagstr).strip()
            step['failure_policy'] = (str(step.get('failure_policy') or '') + ' ' + flagstr).strip()
        if fields_text and step.get('channel') in ('kafka','rabbitmq','queue','event') and not step.get('data_out'):
            step['data_out'] = fields_text
        if meta.get('lookup_keys') and not step.get('data_in'):
            step['data_in'] = meta.get('lookup_keys')
    return payload

# v8.6.71b: audit/reconciliation controls in compact text should count for rules
# that inspect data_out rather than compensation.
_PARSE_PROCESS_V8671B = parse_process

def parse_process(text):
    payload = _PARSE_PROCESS_V8671B(text)
    for s in payload.get('steps') or []:
        blob = ' '.join(str(s.get(k) or '') for k in ('name','compensation','failure_policy','data_out'))
        low = blob.lower()
        if any(x in low for x in ('audit', 'аудит', 'журнал')):
            s['data_out'] = (str(s.get('data_out') or '') + ' audit journal evidence').strip()
        if any(x in low for x in ('reconciliation', 'сверк', 'watermark', 'backfill')):
            s['data_out'] = (str(s.get('data_out') or '') + ' reconciliation watermark backfill').strip()
        if any(x in low for x in ('consumer lag', 'lag', 'backpressure', 'parallelism', 'параллел')):
            s['data_out'] = (str(s.get('data_out') or '') + ' consumer lag backpressure parallelism').strip()
    return payload
