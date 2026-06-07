#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
from integration_architect_pro import Engine, detect_primary_and_modifiers, _is_financial_write


def credit_application_form():
    steps=[
        {'order':1,'actorLabel':'Клиент','action':'Создаёт заявку / запрос','object':'Кредитная заявка'},
        {'order':2,'actorLabel':'Внутренняя система','action':'Принимает заявку','object':'Кредитная заявка'},
        {'order':3,'actorLabel':'Внутренняя система','action':'Проверяет данные','object':'Кредитная заявка'},
        {'order':4,'actorLabel':'Внешняя система','action':'Обрабатывает скоринг','object':'Кредитная заявка'},
        {'order':5,'actorLabel':'Внешняя система','action':'Получает ответ позже','object':'Кредитная заявка'},
        {'order':6,'actorLabel':'Внутренняя система','action':'Обновляет статус','object':'Статус'},
    ]
    return {
        'ux_mode':'business_first_constructor',
        'simple_situation':'async_worker',
        'business_case':'application_creation',
        'business_object':'Кредитная заявка',
        'business_steps_json':json.dumps(steps, ensure_ascii=False),
        'business_result_timing':'Нужно принять сейчас, результат получить позже',
        'business_result_type':'Обновлён статус',
        'business_criticality':'Всё важно',
        'business_constraints_json':json.dumps(['money','active_active','highload','pii','regulatory','compensation','multi_tenant'], ensure_ascii=False),
        'business_goal':'Кредитная заявка проходит скоринг, внешний ответ приходит позже, статус обновляется; это финансовый домен, но не запись баланса/ledger.',
    }


def payment_write_form():
    steps=[
        {'order':1,'actorLabel':'Система','action':'Создаёт платёжную операцию','object':'Платёж / финансовая операция'},
        {'order':2,'actorLabel':'Система','action':'Меняет баланс','object':'Баланс'},
    ]
    return {
        'ux_mode':'business_first_constructor',
        'simple_situation':'event_kafka',
        'business_case':'data_change_distribution',
        'business_object':'Платёж / финансовая операция',
        'business_steps_json':json.dumps(steps, ensure_ascii=False),
        'business_result_timing':'Можно позже',
        'business_result_type':'Данные переданы другой системе',
        'business_criticality':'Всё важно',
        'business_constraints_json':json.dumps(['money','active_active','highload'], ensure_ascii=False),
        'business_goal':'Система создаёт платёжную операцию и меняет баланс в active-active режиме.',
    }


def contract_application_form():
    form=credit_application_form()
    form['business_object']='Договор / кредитная заявка'
    form['business_constraints_json']=json.dumps(['money','active_active'], ensure_ascii=False)
    form['business_goal']='Создание договорной заявки без выдачи кредита, баланса, проводки или обязательства.'
    return form


def test_credit_application_money_active_active_is_saga_not_financial_write():
    form=credit_application_form()
    assert not _is_financial_write(form)
    res=Engine().generate(form)
    assert res['primary_specialized_case']=='saga_state_machine'
    assert 'active_active_warning' in res['secondary_modifiers']
    assert 'financial_domain_controls' in res['secondary_modifiers']
    assert 'Process State DB' in res['case_schema']
    assert 'Compensation' in res['case_schema']
    assert not res['case_schema'].startswith('Region API')
    assert 'Single Writer/Ledger' not in res['case_schema']
    assert 'financial-domain ADR' in res['markdown']
    assert 'Финансовый домен без ledger-write' in res['markdown']


def test_payment_active_active_is_financial_write():
    form=payment_write_form()
    assert _is_financial_write(form)
    res=Engine().generate(form)
    assert res['primary_specialized_case']=='active_active_financial_write'
    assert 'Single Writer/Ledger' in res['case_schema']
    assert 'split-brain' in res['markdown']
    assert 'double' in res['markdown'].lower() or 'двой' in res['markdown'].lower()


def test_contract_application_is_not_financial_write_without_obligation_change():
    form=contract_application_form()
    detected=detect_primary_and_modifiers(form, 'async_worker')
    assert detected['primary']!='active_active_financial_write'
    assert detected['primary'] in ['saga_state_machine','async_worker']
    assert 'active_active_warning' in detected['modifiers']
    assert 'financial_domain_controls' in detected['modifiers']
