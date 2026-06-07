#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
from integration_architect_pro import Engine


def hard_mixed_form():
    steps=[
        {'order':1,'actorLabel':'Клиент','action':'Создаёт заявку / запрос','object':'Заявка'},
        {'order':2,'actorLabel':'Внутренняя система','action':'Принимает заявку','object':'Заявка'},
        {'order':3,'actorLabel':'Внутренняя система','action':'Проверяет данные','object':'Заявка'},
        {'order':4,'actorLabel':'Внешняя система','action':'Обрабатывает запрос','object':'Заявка'},
        {'order':5,'actorLabel':'Внешняя система','action':'Получает ответ позже','object':'Заявка'},
        {'order':6,'actorLabel':'Внутренняя система','action':'Обновляет статус','object':'Статус'},
        {'order':7,'actorLabel':'Оператор','action':'Отправляет на ручной разбор','object':'Заявка'},
    ]
    return {
        'ux_mode':'business_first_constructor',
        'simple_situation':'async_worker',
        'business_case':'application_creation',
        'business_steps_json':json.dumps(steps, ensure_ascii=False),
        'business_object':'Заявка',
        'business_result_timing':'Нужно принять сейчас, результат получить позже',
        'business_result_type':'Обновлён статус',
        'business_criticality':'Всё важно',
        'business_constraints_json':json.dumps(['highload','regulatory','pii','many_consumers','compensation','multi_tenant','active_active','replay','manual','unstable_external'], ensure_ascii=False),
        'business_goal':'Клиент создаёт заявку, внешний провайдер обрабатывает запрос позже, система обновляет статус; нужны компенсации, ручное восстановление, ПДн/регуляторика, highload и multi-tenant.',
    }


def test_hard_mixed_report_has_primary_schema_and_architecture_risk():
    res=Engine().generate(hard_mixed_form())
    md=res['markdown']
    assert res['primary_specialized_case']=='saga_state_machine'
    assert 'multi_tenant_noisy_neighbor' in res['secondary_modifiers']
    assert 'Process State DB' in res['case_schema']
    assert not res['case_schema'].startswith('Shared Stream')
    assert '**Архитектурный риск:** YELLOW' in md


def test_schema_nodes_are_specific_not_generic():
    md=Engine().generate(hard_mixed_form())['markdown']
    assert 'принимает заявку/команду' in md
    assert 'хранит состояние процесса, статусы шагов' in md
    assert 'изолирует работу с внешней системой' in md
    assert 'делает свою часть потока; принимает вход предыдущего блока' not in md


def test_handoff_is_grouped_primary_and_modifiers():
    md=Engine().generate(hard_mixed_form())['markdown']
    for group in ['State machine / статусы / восстановление','Внешний провайдер / callback','Multi-tenant / изоляция нагрузки','Highload / производительность','ПДн / регуляторика / аудит','Active-active / консистентность']:
        assert f'### {group}' in md
    for item in ['process state model','compensation_failed process','tenantId key','backpressure','access control','single-writer decision or ADR']:
        assert item in md


def test_test_cases_cover_primary_and_modifiers():
    md=Engine().generate(hard_mixed_form())['markdown']
    for item in ['partial success: внешний шаг упал после успешной валидации','compensation_failed: компенсация тоже упала','callback пришёл повторно','tenant создаёт lag другим tenant','пиковая нагрузка проходит capacity/load test','PII masking скрывает чувствительные поля','одна операция не исполняется дважды в двух регионах','backfill переигрывает период без дублей']:
        assert item in md


def test_adr_context_is_business_specific_not_generic_services():
    md=Engine().generate(hard_mixed_form())['markdown']
    assert 'клиентская/бизнес-заявка проходит многошаговый процесс' in md
    assert 'Service 1 → Service 2 → Service 3' not in md
