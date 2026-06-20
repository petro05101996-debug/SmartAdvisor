#!/usr/bin/env python3
"""
SmartAdvisor CLI Agent — интерактивный агент архитектурного ревью интеграций.

Зачем: SmartAdvisor — детерминированный движок (engine.py), который находит
архитектурные проблемы интеграций и дыры в требованиях БЕЗ участия LLM. Анализ
не зависит от качества какой-либо модели — это правила, кодирующие экспертизу
системного аналитика. Этот агент даёт диалоговый CLI-интерфейс поверх движка:
ведёт пользователя по шагам описания процесса, строит модель, запускает реальный
аудит и показывает находки с возможностью углубиться.

Запуск:
    python sa_agent.py                 # интерактивный режим (диалог)
    python sa_agent.py --file proc.json   # ревью готового описания из JSON
    python sa_agent.py --demo          # демо на встроенном примере

Команды в интерактивном режиме:
    помощь / help      — список команд
    система / system    — добавить систему-участника
    шаг / step          — добавить шаг процесса
    показать / show     — показать текущую модель
    аудит / audit       — запустить ревью
    сохранить <файл>    — сохранить описание в JSON
    загрузить <файл>    — загрузить описание из JSON
    дыры / gaps         — показать только дыры в требованиях (полнота)
    выход / quit        — выйти
"""
import sys
import json
import argparse

import engine
import process_parser


# ─────────────────────────── презентация ───────────────────────────
RESET = "\033[0m"; BOLD = "\033[1m"; DIM = "\033[2m"
RED = "\033[31m"; YEL = "\033[33m"; GRN = "\033[32m"; CYN = "\033[36m"; MAG = "\033[35m"

SEV_STYLE = {
    "critical": (RED, "КРИТИЧНО"),
    "high":     (YEL, "ВЫСОКИЙ"),
    "medium":   (CYN, "СРЕДНИЙ"),
    "info":     (DIM, "ИНФО"),
}


def c(text, color):
    return f"{color}{text}{RESET}"


def hr(ch="─", n=64):
    print(c(ch * n, DIM))


def banner():
    hr("═")
    print(c("  SmartAdvisor — агент архитектурного ревью интеграций", BOLD))
    print(c("  Детерминированный анализ. Не зависит от LLM.", DIM))
    hr("═")


# ─────────────────────────── сбор модели ───────────────────────────
def new_payload():
    return {"meta": {}, "systems": [], "steps": []}


def ask(prompt, default="", choices=None):
    suffix = f" [{default}]" if default else ""
    if choices:
        suffix += c(f" ({'/'.join(choices)})", DIM)
    while True:
        try:
            val = input(c(f"  {prompt}{suffix}: ", CYN)).strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return default
        if not val:
            return default
        if choices and val.lower() not in choices:
            print(c(f"    выберите из: {', '.join(choices)}", DIM))
            continue
        return val


def ask_yes_no(prompt, default=False):
    d = "да" if default else "нет"
    v = ask(prompt, d, ["да", "нет", "yes", "no"]).lower()
    return v in ("да", "yes")


def collect_meta(payload):
    print(c("\n── Контекст процесса ──", BOLD))
    m = payload["meta"]
    m["name"] = ask("Название процесса", m.get("name", ""))
    m["entity"] = ask("Главная сущность (Order, Payment...)", m.get("entity", "Entity"))
    m["goal"] = ask("Бизнес-цель процесса", m.get("goal", ""))
    m["money"] = ask("Деньги в процессе", m.get("money", "no"), ["no", "indirect", "direct"]).lower()
    m["customer_visible"] = "да" if ask_yes_no("Виден ли процесс клиенту?", False) else "no"
    m["regulatory"] = ask_yes_no("Есть регуляторные требования?", False)
    sla = ask("Целевой SLA в мс (0 = асинхронно)", str(m.get("sla_ms", 0)))
    m["sla_ms"] = int(sla) if sla.isdigit() else 0
    m["ordering"] = ask("Нужен порядок обработки", m.get("ordering", "no"), ["no", "per_entity", "global"]).lower()


def collect_system(payload):
    print(c("\n── Новая система-участник ──", BOLD))
    name = ask("Имя системы")
    if not name:
        print(c("    отменено", DIM)); return
    role = ask("Роль", "internal", ["internal", "external", "broker", "db", "legacy", "analytics"]).lower()
    stability = ask("Стабильность", "unknown", ["stable", "unstable", "limited", "unknown"]).lower()
    crit = ask("Критичность", "medium", ["low", "medium", "high"]).lower()
    payload["systems"].append({"name": name, "role": role, "stability": stability, "criticality": crit})
    print(c(f"  + система «{name}» ({role})", GRN))


def collect_step(payload):
    print(c("\n── Новый шаг процесса ──", BOLD))
    name = ask("Что происходит на шаге")
    if not name:
        print(c("    отменено", DIM)); return
    order = len(payload["steps"]) + 1
    prev_target = payload["steps"][-1].get("target_system") if payload.get("steps") else "Инициатор процесса"
    source = ask("Источник связи / кто отдаёт данные", prev_target or "Инициатор процесса")
    target = ask("Получатель связи / куда идут данные")
    executor = ask("Какая система выполняет шаг", source or target)
    channel = ask("Канал/протокол", "rest", ["rest", "grpc", "soap", "graphql", "kafka", "rabbitmq", "queue", "event", "db", "file", "batch"]).lower()
    step = {
        "order": order,
        "name": name,
        "system": executor,
        "source_system": source,
        "target_system": target,
        "producer": source,
        "consumer": target,
        "channel": channel,
        "blocking": ask_yes_no("Блокирует ли процесс (ждём ответа)?", channel in ("rest", "grpc", "soap", "graphql", "db")),
        "writes_entity": ask_yes_no("Изменяет ли главную сущность (запись)?", False),
        "retry": ask("Повторы при сбое", "none", ["none", "auto", "manual"]).lower(),
        "idempotency": ask("Идемпотентность", "none", ["none", "key", "natural"]).lower(),
    }
    to = ask("Таймаут в мс (0 = не задан)", "0")
    step["timeout_ms"] = int(to) if to.isdigit() else 0
    if order > 1:
        dep = ask(f"От какого шага зависит (1..{order-1}, пусто = от предыдущего)", str(order - 1))
        step["depends_on"] = int(dep) if dep.isdigit() else order - 1
    payload["steps"].append(step)
    print(c(f"  + шаг {order}: «{name}» {source} → {target} ({channel})", GRN))


def show_model(payload):
    m = payload["meta"]
    print(c("\n── Текущая модель ──", BOLD))
    print(f"  Процесс: {c(m.get('name','—'), BOLD)} | сущность: {m.get('entity','—')} | деньги: {m.get('money','no')}")
    print(c(f"  Системы ({len(payload['systems'])}):", BOLD))
    for s in payload["systems"]:
        print(f"    • {s['name']} — {s.get('role','internal')}, {s.get('stability','unknown')}")
    print(c(f"  Шаги ({len(payload['steps'])}):", BOLD))
    for st in payload["steps"]:
        flags = []
        if st.get("blocking"): flags.append("blocking")
        if st.get("writes_entity"): flags.append("write")
        if st.get("retry", "none") != "none": flags.append(f"retry:{st['retry']}")
        fl = c("  [" + ", ".join(flags) + "]", DIM) if flags else ""
        src = st.get("source_system") or "источник не указан"
        tgt = st.get("target_system") or st.get("system") or "получатель не указан"
        print(f"    {st['order']}. {st['name']}: {src} → {tgt} ({st['channel']}){fl}")


def present_understanding(result):
    info = result.get("process_understanding") or {}
    if not info:
        return
    conf = (info.get("confidence") or {})
    pct = conf.get("confidence_pct")
    color = GRN if (pct or 0) >= 80 else (YEL if (pct or 0) >= 60 else RED)
    print(c("\n  ── Я понял процесс так ──", BOLD))
    print(c(f"  Уверенность карты процесса: {pct}% ({conf.get('confidence','—')})", color))
    if conf.get("blockers"):
        print(c("  Блокеры карты:", RED))
        for b in conf.get("blockers", [])[:5]: print(f"    • {b}")
    if conf.get("warnings"):
        print(c("  Требует подтверждения:", YEL))
        for w in conf.get("warnings", [])[:5]: print(f"    • {w}")
    for st in info.get("steps", [])[:12]:
        print(f"    {st.get('order')}. {st.get('route')} — {st.get('title')} [{st.get('channel')}]" )


# ─────────────────────────── аудит и вывод ───────────────────────────
def run_audit(payload):
    if not payload["steps"]:
        print(c("\n  Нет шагов для анализа. Добавьте хотя бы один шаг (команда: шаг).", YEL))
        return None
    print(c("\n  Запускаю детерминированный аудит...", DIM))
    result = engine.analyze(payload)
    if not result.get("ok"):
        print(c("\n  Модель некорректна:", RED))
        for e in result.get("errors", []):
            print(f"    • {e}")
        return None
    present_verdict(result)
    present_understanding(result)
    present_grouped(result)
    present_completeness(result.get("completeness", {}), brief=True)
    print(c("\n  Команды: «детали» — все находки подробно · «дыры» — полнота требований · «аудит» — заново\n", DIM))
    return result


def present_verdict(result):
    v = result["verdict"]
    color = {"red": RED, "yellow": YEL, "green": GRN}.get(v.get("color"), RESET)
    hr("═")
    print(f"  {c('ВЕРДИКТ:', BOLD)} {c(v.get('verdict','—'), color)}")
    print(f"  Оценка готовности: {c(str(v.get('score','—')) + '/10', color)}")
    cn = v.get("counts", {})
    print(f"  Находки: "
          f"{c(str(cn.get('critical',0)) + ' критич.', RED)}, "
          f"{c(str(cn.get('high',0)) + ' выс.', YEL)}, "
          f"{c(str(cn.get('medium',0)) + ' сред.', CYN)}, "
          f"{c(str(cn.get('info',0)) + ' инфо', DIM)}")
    hr("═")


SEV_ORDER = {"critical": 0, "high": 1, "medium": 2, "info": 3}


def present_grouped(result):
    """Сгруппированный, приоритизированный вид: дубли свёрнуты, видно с чего начать."""
    groups = result.get("finding_groups") or []
    if not groups:
        print(c("\n  Проблем не найдено.", GRN)); return
    groups = sorted(groups, key=lambda g: SEV_ORDER.get(g.get("severity", "info"), 9))

    # «С чего начать» — топ-3 по серьёзности.
    blockers = [g for g in groups if g.get("severity") in ("critical", "high")]
    if blockers:
        print(c("\n  ▶ С ЧЕГО НАЧАТЬ (блокеры):", BOLD + RED))
        for i, g in enumerate(blockers[:3], 1):
            where = g.get("where_summary") or g.get("where") or ""
            cnt = g.get("count", 1)
            tag = c(f" ×{cnt}", DIM) if cnt > 1 else ""
            print(f"    {c(str(i)+'.', BOLD)} {g.get('title','')}{tag}")
            if where:
                print(c(f"       {where}", DIM))

    # Полный сгруппированный список по категориям.
    print(c(f"\n  ── Все находки, сгруппировано ({len(groups)} групп) ──", BOLD))
    by_cat = {}
    for g in groups:
        by_cat.setdefault(g.get("category", "Прочее"), []).append(g)
    for cat, gs in by_cat.items():
        print(c(f"\n  {cat}", BOLD + CYN))
        for g in gs:
            color, label = SEV_STYLE.get(g.get("severity", "info"), (RESET, "?"))
            cnt = g.get("count", 1)
            tag = c(f" ×{cnt}", DIM) if cnt > 1 else ""
            where = g.get("where_summary") or g.get("where") or ""
            print(f"    {c('●', color)} {c(f'[{label}]', color)} {g.get('title','')}{tag}")
            if where:
                print(c(f"        {where}", DIM))


def present_details(result):
    """Полный разбор каждой группы с причиной и фиксом (по команде «детали»)."""
    groups = result.get("finding_groups") or []
    groups = sorted(groups, key=lambda g: SEV_ORDER.get(g.get("severity", "info"), 9))
    print(c(f"\n── Подробно: {len(groups)} находок ──", BOLD))
    for g in groups:
        color, label = SEV_STYLE.get(g.get("severity", "info"), (RESET, "?"))
        cnt = g.get("count", 1)
        tag = c(f"  (затрагивает {cnt})", DIM) if cnt > 1 else ""
        print(f"\n  {c(f'[{label}]', color)} {c(g.get('title',''), BOLD)}{tag}")
        where = g.get("where_summary") or g.get("where") or ""
        if where:
            print(c(f"     где:  {where}", DIM))
        if g.get("why"):
            print(f"     {c('почему:', DIM)} {g['why']}")
        if g.get("fix"):
            print(f"     {c('как:', GRN)}   {g['fix']}")


def present_completeness(comp, brief=False):
    if not comp:
        return
    pct = comp.get("score_pct", 0)
    conf = comp.get("confidence", "—")
    color = GRN if pct >= 70 else (YEL if pct >= 40 else RED)
    missing = comp.get("missing", [])
    if brief:
        high = [m for m in missing if m.get("priority") == "high"]
        print(c(f"\n  Полнота требований: {pct}% (уверенность: {conf})", color)
              + c(f" — {len(missing)} незакрытых вопросов, из них {len(high)} важных", DIM))
        return
    print(c(f"\n── Полнота требований: {pct}% (уверенность: {conf}) ──", BOLD))
    if missing:
        print(c("  Дыры в требованиях — что не описано:", color))
        for mss in missing[:8]:
            pr = mss.get("priority", "")
            pc = {"high": RED, "medium": YEL}.get(pr, DIM)
            print(f"    {c('•', pc)} [{mss.get('area','')}] {mss.get('question','')}")
            if mss.get("why"):
                print(c(f"        почему важно: {mss['why']}", DIM))


def show_gaps_only(payload):
    """Только дыры в требованиях — быстрый режим без полного аудита."""
    if not payload["steps"]:
        print(c("\n  Нет шагов. Добавьте шаги или загрузите описание.", YEL)); return
    result = engine.analyze(payload)
    if not result.get("ok"):
        print(c("\n  Модель некорректна для проверки полноты.", RED)); return
    present_completeness(result.get("completeness", {}))


# ─────────────────────────── интерактивный цикл ───────────────────────────
HELP = """
  Команды:
    опиши    (describe) — ОПИСАТЬ ПРОЦЕСС ТЕКСТОМ (быстрый путь)
    система  (system)   — добавить систему-участник
    шаг      (step)     — добавить шаг процесса
    контекст (meta)     — задать/изменить контекст процесса
    показать (show)     — показать текущую модель
    аудит    (audit)    — запустить полное ревью
    дыры     (gaps)     — показать только дыры в требованиях
    детали   (details)  — все находки подробно (после аудита)
    сохранить <файл>    — сохранить описание в JSON
    загрузить <файл>    — загрузить описание из JSON
    помощь   (help)     — эта справка
    выход    (quit)     — выйти
"""


def echo_parsed(payload):
    """Показать пользователю, что агент ПОНЯЛ из текста — чтобы он мог поправить."""
    m = payload.get("meta", {})
    print(c("\n  Я понял так:", BOLD + GRN))
    if m.get("name") or m.get("entity"):
        bits = []
        if m.get("name"): bits.append(f"процесс «{m['name']}»")
        if m.get("entity"): bits.append(f"сущность {m['entity']}")
        if m.get("money") and m["money"] != "no": bits.append(f"деньги: {m['money']}")
        if m.get("sla_ms"): bits.append(f"SLA {m['sla_ms']}мс")
        print(c("    " + ", ".join(bits), DIM))
    print(c(f"    Систем: {len(payload['systems'])}", DIM))
    for s in payload["systems"]:
        extra = []
        if s.get("role") != "internal": extra.append(s["role"])
        if s.get("stability") not in ("unknown", None): extra.append(s["stability"])
        ex = c(f" ({', '.join(extra)})", DIM) if extra else ""
        print(f"      • {s['name']}{ex}")
    print(c(f"    Шагов: {len(payload['steps'])}", DIM))
    for st in payload["steps"]:
        flags = []
        if st.get("blocking"): flags.append("блок")
        if st.get("writes_entity"): flags.append("пишет")
        if st.get("retry", "none") != "none": flags.append(f"retry:{st['retry']}")
        if st.get("idempotency", "none") != "none": flags.append(f"идемп:{st['idempotency']}")
        fl = c("  [" + ", ".join(flags) + "]", DIM) if flags else ""
        dep = c(f"  ←{st['depends_on']}", DIM) if st.get("depends_on") else ""
        src = st.get("source_system") or "источник не указан"
        tgt = st.get("target_system") or st.get("system") or "получатель не указан"
        print(f"      {st['order']}. {st['name']}: {src} → {tgt} ({st['channel']}){fl}{dep}")


DESCRIBE_HELP = """
  Опиши процесс — по строке на шаг, в формате:
      действие | источник -> получатель | канал | флаги

  Старый формат тоже работает:
      действие | система | канал | флаги

  Можно начать с контекста (строки до шагов):
      процесс: Оплата заказа
      сущность: Order
      деньги: direct        (direct / indirect / no)
      клиенту: да
      sla: 2000             (мс; 0 = асинхронно)
      нагрузка: 300 x4      (rps и пиковый множитель)

  Шаги (флаги необязательны, канал угадывается):
      принять заказ | Клиент -> API | rest | пишет
      списать оплату | API -> PaymentGW(внешняя, нестабильная) | rest | блокирует
      сохранить статус | API -> DB(база) | db | пишет, идемпотентность:key
      опубликовать событие | API -> Kafka | kafka | <-3

  Флаги: пишет · блокирует · неблокирует · retry:auto · идемпотентность:key ·
         таймаут:3000 · зависимость <-N (по умолчанию от предыдущего шага)

  Завершите ввод пустой строкой или словом «конец».
"""


def describe_by_text(existing=None):
    """Главный удобный путь: пользователь описывает процесс текстом."""
    print(DESCRIBE_HELP)
    print(c("  Вводите описание (Enter на пустой строке — закончить):\n", DIM))
    lines = []
    while True:
        try:
            ln = input(c("  ... ", CYN))
        except (EOFError, KeyboardInterrupt):
            break
        if ln.strip().lower() in ("", "конец", "end", "done"):
            break
        lines.append(ln)
    text = "\n".join(lines)
    if not text.strip():
        print(c("  Пусто — отменено.", DIM))
        return existing
    payload = process_parser.parse_process(text)
    if not payload["steps"]:
        print(c("  Не распознал ни одного шага. Проверьте формат (см. пример выше).", YEL))
        return existing
    echo_parsed(payload)
    print(c("\n  Запускаю аудит... (если что-то понято неверно — поправьте текст и введите «опиши» снова)", DIM))
    return payload


def interactive(payload=None):
    banner()
    payload = payload or new_payload()
    print(c("\n  Самый быстрый способ — команда «опиши»: опишите процесс текстом", BOLD))
    print(c("  (по строке на шаг), и агент сам разложит его и проверит.", DIM))
    print(c("  Либо добавляйте системы и шаги по одному. «помощь» — все команды.\n", DIM))

    aliases = {
        "system": "система", "step": "шаг", "meta": "контекст", "show": "показать",
        "audit": "аудит", "gaps": "дыры", "help": "помощь", "quit": "выход", "exit": "выход",
        "save": "сохранить", "load": "загрузить", "details": "детали", "detail": "детали",
        "describe": "опиши", "text": "опиши", "опиши процесс": "опиши",
        "review": "ревью", "questions": "вопросы", "question": "вопросы",
        "package": "пакет", "pack": "пакет", "pkg": "пакет",
    }
    last_result = None
    # Сразу предложить удобный путь.
    if not payload["steps"]:
        if ask_yes_no("Описать процесс текстом сейчас?", True):
            new = describe_by_text(payload)
            if new and new.get("steps"):
                payload = new
                last_result = run_audit(payload)

    while True:
        try:
            raw = input(c("\nsa> ", BOLD + MAG)).strip()
        except (EOFError, KeyboardInterrupt):
            print(c("\n  Выход.", DIM)); break
        if not raw:
            continue
        parts = raw.split(maxsplit=1)
        cmd = aliases.get(parts[0].lower(), parts[0].lower())
        arg = parts[1] if len(parts) > 1 else ""

        if cmd == "помощь":
            print(HELP)
        elif cmd == "опиши":
            new = describe_by_text(payload)
            if new and new.get("steps"):
                payload = new
                last_result = run_audit(payload)
        elif cmd == "система":
            collect_system(payload)
        elif cmd == "шаг":
            collect_step(payload)
        elif cmd == "контекст":
            collect_meta(payload)
        elif cmd == "показать":
            show_model(payload)
        elif cmd == "аудит":
            last_result = run_audit(payload)
        elif cmd == "детали":
            if last_result:
                present_details(last_result)
            else:
                print(c("  Сначала запустите «аудит».", YEL))
        elif cmd == "ревью":
            if last_result:
                present_solution_review(last_result)
            else:
                print(c("  Сначала запустите «аудит».", YEL))
        elif cmd == "вопросы":
            if last_result:
                present_questions(last_result)
            else:
                print(c("  Сначала запустите «аудит».", YEL))
        elif cmd == "пакет":
            if last_result:
                present_project_package(last_result)
            else:
                print(c("  Сначала запустите «аудит».", YEL))
        elif cmd == "дыры":
            show_gaps_only(payload)
        elif cmd == "сохранить":
            path = arg or "process.json"
            with open(path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            print(c(f"  Сохранено в {path}", GRN))
        elif cmd == "загрузить":
            path = arg or "process.json"
            try:
                with open(path, encoding="utf-8") as f:
                    payload = json.load(f)
                print(c(f"  Загружено из {path}", GRN))
                show_model(payload)
            except Exception as e:
                print(c(f"  Не удалось загрузить: {e}", RED))
        elif cmd == "выход":
            print(c("  Выход.", DIM)); break
        else:
            print(c(f"  Неизвестная команда «{cmd}». Введите «помощь».", YEL))


# ─────────────────────────── демо / файл ───────────────────────────
DEMO = {
    "meta": {"name": "Оплата заказа", "entity": "Order", "money": "direct",
             "customer_visible": "yes", "sla_ms": 2000, "goal": "Принять оплату и подтвердить заказ"},
    "systems": [
        {"name": "API", "role": "internal", "stability": "stable"},
        {"name": "PaymentGW", "role": "external", "stability": "unstable", "criticality": "high"},
        {"name": "DB", "role": "db"},
        {"name": "Analytics", "role": "analytics"},
    ],
    "steps": [
        {"order": 1, "name": "Принять заказ", "system": "API", "channel": "rest", "writes_entity": True},
        {"order": 2, "name": "Списать оплату", "system": "PaymentGW", "channel": "rest",
         "blocking": True, "depends_on": 1},
        {"order": 3, "name": "Сохранить статус оплаты", "system": "DB", "channel": "rest",
         "depends_on": 2, "writes_entity": True},
        {"order": 4, "name": "Отправить событие в аналитику", "system": "Analytics",
         "channel": "rest", "blocking": True, "depends_on": 3},
    ],
}


def main():
    ap = argparse.ArgumentParser(description="SmartAdvisor CLI Agent")
    ap.add_argument("--file", help="JSON-описание процесса для ревью")
    ap.add_argument("--demo", action="store_true", help="запустить на демо-примере")
    ap.add_argument("--gaps", action="store_true", help="только дыры в требованиях (с --file/--demo)")
    ap.add_argument("--details", action="store_true", help="полный разбор всех находок")
    ap.add_argument("--review", action="store_true", help="показать жёсткое ревью готового решения")
    ap.add_argument("--questions", action="store_true", help="показать вопросы к бизнесу/разработке/эксплуатации")
    ap.add_argument("--package", action="store_true", help="показать проектный пакет: карта, контракты, ошибки, ADR")
    ap.add_argument("--text", help="файл с текстовым описанием процесса (компактный формат)")
    ap.add_argument("--schema", action="store_true", help="показать формат JSON + готовый промпт для вашей LLM")
    args = ap.parse_args()

    if args.schema:
        print(LLM_PROMPT)
        return
    if args.text:
        with open(args.text, encoding="utf-8") as f:
            payload = process_parser.parse_process(f.read())
        banner()
        echo_parsed(payload)
        if args.gaps: show_gaps_only(payload)
        else:
            r = run_audit(payload)
            if args.details and r: present_details(r)
            if args.review and r: present_solution_review(r)
            if args.questions and r: present_questions(r)
            if args.package and r: present_project_package(r)
        return
    if args.demo:
        banner()
        print(c("\n  Демо-пример: «Оплата заказа»\n", DIM))
        if args.gaps: show_gaps_only(DEMO)
        else:
            r = run_audit(DEMO)
            if args.details and r: present_details(r)
            if args.review and r: present_solution_review(r)
            if args.questions and r: present_questions(r)
            if args.package and r: present_project_package(r)
        return
    if args.file:
        payload = load_payload_robust(args.file)
        banner()
        if payload is None:
            print(c("  Не удалось извлечь форму процесса из ввода.", RED)); return
        if args.gaps: show_gaps_only(payload)
        else:
            r = run_audit(payload)
            if args.details and r: present_details(r)
            if args.review and r: present_solution_review(r)
            if args.questions and r: present_questions(r)
            if args.package and r: present_project_package(r)
        return
    interactive()


def extract_json(text):
    """Достать JSON-форму из любого вывода модели: голый JSON, ```json...```,
    или JSON с текстом вокруг («Вот ваша форма: {...}»). Модели редко отдают
    чистый JSON, поэтому агент терпим к обёртке."""
    text = text.strip()
    # 1) попытка как есть
    try:
        return json.loads(text)
    except Exception:
        pass
    # 2) вырезать из markdown-блока ```json ... ```
    import re
    m = re.search(r"```(?:json)?\s*(.+?)```", text, re.S)
    if m:
        try:
            return json.loads(m.group(1).strip())
        except Exception:
            pass
    # 3) найти первый сбалансированный {...}
    start = text.find("{")
    if start != -1:
        depth = 0
        for i in range(start, len(text)):
            if text[i] == "{": depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start:i + 1])
                    except Exception:
                        break
    return None


def load_payload_robust(source):
    """source = путь к файлу или '-' для stdin. Принимает JSON-форму (в т.ч.
    'грязную' из вывода модели). Так твоя модель может отдать форму как угодно —
    конвейером `модель | sa_agent.py --file -` или файлом."""
    if source == "-":
        raw = sys.stdin.read()
    else:
        with open(source, encoding="utf-8") as f:
            raw = f.read()
    return extract_json(raw)


LLM_PROMPT = r'''
═══════════════════════════════════════════════════════════════════
 ФОРМАТ ДЛЯ ВАШЕЙ МОДЕЛИ
═══════════════════════════════════════════════════════════════════
Дайте вашей LLM этот промпт. Она превратит свободное описание процесса
в JSON, который понимает агент. Затем:

    ваша_модель "<промпт + описание>" | python sa_agent.py --file -

или сохраните вывод модели в файл и:  python sa_agent.py --file out.json
Агент терпим к обёртке: JSON можно отдавать в ```json```, с текстом вокруг — извлечётся.

─── ПРОМПТ ДЛЯ LLM (скопируйте) ───────────────────────────────────
Ты — конвертер описания интеграции в строгий JSON. На вход — свободное
описание бизнес-процесса/интеграции. Верни ТОЛЬКО JSON по схеме ниже,
без пояснений.

Схема:
{
  "meta": {
    "name": "строка — название процесса",
    "entity": "главная сущность (Order, Payment, Booking...)",
    "money": "no | indirect | direct",
    "customer_visible": "yes | no",
    "regulatory": true/false,
    "sla_ms": число (0 = асинхронно/не задано),
    "ordering": "no | per_entity | global",
    "load_rps": число (0 если неизвестно),
    "peak_factor": число (1 если неизвестно)
  },
  "systems": [
    {"name":"имя", "role":"internal|external|broker|db|legacy|analytics",
     "stability":"stable|unstable|limited|unknown", "criticality":"low|medium|high",
     "rate_limit_rps": число (0 если неизвестно)}
  ],
  "steps": [
    {"order":1, "name":"что делает шаг",
     "system":"исполнитель шага",
     "source_system":"кто отдаёт данные/инициирует связь",
     "target_system":"кто получает данные/результат",
     "producer":"производитель события/запроса",
     "consumer":"потребитель события/запроса",
     "channel":"rest|grpc|soap|graphql|kafka|rabbitmq|queue|event|db|file|batch",
     "blocking":true/false, "writes_entity":true/false,
     "retry":"none|auto|manual", "idempotency":"none|key|natural",
     "timeout_ms":число, "depends_on":номер предыдущего шага (0 если первый),
     "compensation":"строка — компенсирующее действие, если есть"}
  ]
}

Правила вывода:
- Для каждого шага обязательно заполни source_system и target_system: кто → кому.
- system = исполнитель шага, но не подменяй им источник и получателя.
- Внешние API/УК/партнёры → role external; очереди/Kafka → broker; БД → db; DWH/аналитика → analytics.
- writes_entity=true для шагов сохранения/создания/проводки сущности.
- blocking=true для синхронных вызовов, ждущих ответа.
- Если параметр не известен из текста — ставь разумный дефолт из схемы.
- depends_on по умолчанию = предыдущий шаг.
- Если обычный текст не позволяет уверенно определить карту процесса, добавь в meta: {"input_quality":"needs_confirmation"}.
Верни только JSON.
─────────────────────────────────────────────────────────────────
'''


# ---------------------------------------------------------------------------
# v8.6.69: команды рабочего продукта — ревью, вопросы, проектный пакет.
def present_readiness_matrix(result):
    matrix = result.get('readiness_matrix') or []
    if not matrix:
        return
    print(c("\n  ── Матрица готовности ──", BOLD))
    for item in matrix:
        ok = bool(item.get('ok'))
        color = GRN if ok else RED
        mark = 'OK' if ok else 'FAIL'
        print(f"  {c(mark, color)} {item.get('name')}: {item.get('next_step')}")
        for r in (item.get('reasons') or [])[:3]:
            print(c(f"      • {r}", DIM))


def present_questions(result):
    q = result.get('questions') or {}
    if not q:
        return
    print(c("\n  ── Вопросы, которые надо задать ──", BOLD))
    labels = [('business','К бизнесу'), ('development','К разработке'), ('operations','К эксплуатации'), ('architecture_review','К архитектору/ревью')]
    for key, title in labels:
        vals = q.get(key) or []
        if not vals:
            continue
        print(c(f"\n  {title}:", CYN))
        for v in vals[:6]:
            print(f"    • {v}")


def present_solution_review(result):
    review = result.get('solution_review') or {}
    if not review:
        return
    print(c("\n  ── Жёсткое ревью решения ──", BOLD))
    strengths = review.get('strengths') or []
    if strengths:
        print(c("  Что уже полезно:", GRN))
        for s in strengths[:5]:
            print(f"    • {s}")
    blockers = review.get('blockers') or []
    print(c("  Что мешает отдавать дальше:", RED if blockers else GRN))
    if blockers:
        for b in blockers[:8]:
            print(f"    • [{b.get('severity')}] {b.get('title')}")
            if b.get('fix'):
                print(c(f"      исправить: {b.get('fix')}", DIM))
    else:
        print("    • critical/high-блокеров не найдено")
    actions = review.get('first_actions') or []
    if actions:
        print(c("  Первые действия:", YEL))
        for i, a in enumerate(actions[:6], 1):
            print(f"    {i}. {a}")


def present_project_package(result):
    pkg = result.get('project_package') or {}
    if not pkg:
        return
    print(c("\n  ── Проектный пакет ──", BOLD))
    summary = pkg.get('executive_summary') or {}
    print(f"  Процесс: {summary.get('process','—')} | сущность: {summary.get('entity','—')} | readiness: {summary.get('readiness','—')}")
    print(c("\n  Карта процесса:", CYN))
    for st in (pkg.get('process_map') or [])[:10]:
        print(f"    {st.get('order')}. {st.get('from')} → {st.get('to')} ({st.get('channel_label')}) — {st.get('title')}")
    print(c("\n  Контракты:", CYN))
    for ct in (pkg.get('contracts') or [])[:6]:
        print(f"    • {ct.get('kind')} {ct.get('name')} · {ct.get('route')}")
    print(c("\n  Ошибки/восстановление по шагам:", CYN))
    for row in (pkg.get('errors_by_step') or [])[:6]:
        print(f"    • Шаг {row.get('step')} {row.get('route')}: {', '.join(row.get('controls') or [])}")
    print(c("\n  ADR:", CYN))
    for adr in (pkg.get('adr') or [])[:5]:
        print(f"    • {adr.get('decision')} — {adr.get('why')}")

# расширяем help/aliases и run_audit без переписывания старого цикла полностью
HELP = HELP.replace('    детали   (details)  — все находки подробно (после аудита)', '    детали   (details)  — все находки подробно (после аудита)\n    ревью    (review)   — жёсткое ревью готового решения\n    вопросы  (questions)— вопросы к бизнесу/разработке/эксплуатации\n    пакет    (package)  — проектный пакет: карта, контракты, ошибки, ADR, тесты')

_OLD_RUN_AUDIT_V8669 = run_audit

def run_audit(payload):
    result = _OLD_RUN_AUDIT_V8669(payload)
    if result:
        present_readiness_matrix(result)
        print(c("\n  Новые команды: «ревью» · «вопросы» · «пакет» показывают рабочие проектные артефакты.\n", DIM))
    return result

# Поддержка CLI flags без ломки interactive: оборачиваем main нельзя безопасно,
# поэтому добавляем быстрые функции для импортных/тестовых сценариев.
def product_review_text(payload):
    res = engine.analyze(payload)
    if not res.get('ok'):
        return {'ok': False, 'errors': res.get('errors')}
    return {'ok': True, 'solution_review': res.get('solution_review'), 'questions': res.get('questions'), 'readiness_matrix': res.get('readiness_matrix'), 'project_package': res.get('project_package')}


if __name__ == "__main__":
    main()
