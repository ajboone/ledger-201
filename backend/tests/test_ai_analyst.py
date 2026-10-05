import json
from datetime import datetime
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import models
from app.services.ai_analyst import (
    AIAnalystConfigurationError,
    AIAnalystInvalidToolCallError,
    AIAnalystProviderError,
    AIAnalystToolLimitError,
    MAX_TOOL_CALL_ITERATIONS,
    run_ai_analyst_query,
)
from app.services.daily_review import LocationNotFoundError


class FakeResponses:
    def __init__(self, responses: list[object]) -> None:
        self.responses_to_return = responses
        self.calls: list[dict[str, object]] = []

    def create(self, **kwargs: object) -> object:
        self.calls.append(kwargs)
        if not self.responses_to_return:
            raise AssertionError("Unexpected Responses API request.")
        return self.responses_to_return.pop(0)


def _function_call(name: str, arguments: str, call_id: str) -> object:
    return SimpleNamespace(
        type="function_call",
        name=name,
        arguments=arguments,
        call_id=call_id,
    )


def _response(output: list[object], answer: str = "") -> object:
    return SimpleNamespace(output=output, output_text=answer)


def _fake_client(*responses: object) -> tuple[object, FakeResponses]:
    fake_responses = FakeResponses(list(responses))
    return SimpleNamespace(responses=fake_responses), fake_responses


def _seed_ai_data(db: Session) -> int:
    location = models.Location(
        name="AI Analyst Sushi",
        timezone="America/New_York",
        currency="USD",
    )
    first_order = models.Order(
        square_order_id="AI-ORDER-1",
        location=location,
        state="COMPLETED",
        currency="USD",
        created_at=datetime(2026, 9, 12, 18, 0),
        subtotal_amount=1000,
        discount_amount=100,
        tax_amount=72,
        service_charge_amount=0,
        total_amount=972,
        line_items=[
            models.OrderLineItem(
                item_name="Salmon Roll",
                category_name="Rolls",
                quantity=1,
                unit_price_amount=1000,
                gross_sales_amount=1000,
                discount_amount=100,
                total_amount=900,
            )
        ],
        payments=[
            models.Payment(
                square_payment_id="AI-PAYMENT-1",
                status="COMPLETED",
                currency="USD",
                amount=972,
                refunds=[
                    models.Refund(
                        square_refund_id="AI-REFUND-1",
                        status="COMPLETED",
                        currency="USD",
                        amount=100,
                    )
                ],
            )
        ],
    )
    second_order = models.Order(
        square_order_id="AI-ORDER-2",
        location=location,
        state="COMPLETED",
        currency="USD",
        created_at=datetime(2026, 9, 13, 18, 0),
        subtotal_amount=2000,
        discount_amount=0,
        tax_amount=144,
        service_charge_amount=0,
        total_amount=2144,
        line_items=[
            models.OrderLineItem(
                item_name="Tuna Roll",
                category_name="Rolls",
                quantity=2,
                unit_price_amount=1000,
                gross_sales_amount=2000,
                discount_amount=0,
                total_amount=2000,
            )
        ],
        payments=[
            models.Payment(
                square_payment_id="AI-PAYMENT-2",
                status="COMPLETED",
                currency="USD",
                amount=2144,
            )
        ],
    )
    db.add_all([first_order, second_order])
    db.commit()
    return location.id


def _run(
    db: Session,
    client: object,
    location_id: int,
    question: str = "Summarize September 12, 2026.",
):
    return run_ai_analyst_query(
        db,
        location_id,
        question,
        client=client,
        model="test-model",
    )


def test_simple_question_calls_one_deterministic_tool(
    db_session: Session,
) -> None:
    location_id = _seed_ai_data(db_session)
    client, fake_responses = _fake_client(
        _response(
            [
                _function_call(
                    "get_daily_summary",
                    '{"review_date":"2026-09-12"}',
                    "call-summary",
                )
            ]
        ),
        _response([SimpleNamespace(type="message")], "Sales were $9.72."),
    )

    result = _run(db_session, client, location_id)

    assert result.answer == "Sales were $9.72."
    assert len(result.tool_calls_used) == 1
    assert result.tool_calls_used[0].tool == "get_daily_summary"
    assert result.tool_calls_used[0].arguments == {
        "review_date": "2026-09-12",
        "location_id": location_id,
    }
    tool_output = fake_responses.calls[1]["input"][-1]
    serialized = json.loads(tool_output["output"])
    assert serialized["currency"] == "USD"
    assert serialized["order_total_amount"] == 972
    assert isinstance(serialized["order_total_amount"], int)


def test_model_can_call_multiple_tools_across_iterations(
    db_session: Session,
) -> None:
    location_id = _seed_ai_data(db_session)
    client, fake_responses = _fake_client(
        _response(
            [
                _function_call(
                    "get_daily_summary",
                    '{"review_date":"2026-09-12"}',
                    "call-first",
                )
            ]
        ),
        _response(
            [
                _function_call(
                    "get_refund_summary",
                    '{"review_date":"2026-09-12"}',
                    "call-second",
                )
            ]
        ),
        _response([SimpleNamespace(type="message")], "One completed refund."),
    )

    result = _run(db_session, client, location_id)

    assert [call.tool for call in result.tool_calls_used] == [
        "get_daily_summary",
        "get_refund_summary",
    ]
    assert len(fake_responses.calls) == 3
    second_input = fake_responses.calls[1]["input"]
    assert any(
        getattr(item, "call_id", None) == "call-first"
        for item in second_input
    )
    assert second_input[-1]["call_id"] == "call-first"
    third_input = fake_responses.calls[2]["input"]
    assert third_input[-1]["call_id"] == "call-second"


def test_comparison_question_calls_comparison_tool(
    db_session: Session,
) -> None:
    location_id = _seed_ai_data(db_session)
    client, fake_responses = _fake_client(
        _response(
            [
                _function_call(
                    "compare_daily_performance",
                    '{"date_a":"2026-09-12","date_b":"2026-09-13"}',
                    "call-compare",
                )
            ]
        ),
        _response([SimpleNamespace(type="message")], "Net collections increased."),
    )

    result = _run(
        db_session,
        client,
        location_id,
        "Compare September 12 and September 13, 2026.",
    )

    assert result.tool_calls_used[0].tool == "compare_daily_performance"
    assert result.tool_calls_used[0].arguments["date_a"] == "2026-09-12"
    assert result.tool_calls_used[0].arguments["date_b"] == "2026-09-13"
    comparison_output = fake_responses.calls[1]["input"][-1]["output"]
    comparison = json.loads(comparison_output)
    assert comparison["currency"] == "USD"
    assert comparison["order_total_change"] == 1172


def test_final_answer_without_tool_is_returned(
    db_session: Session,
) -> None:
    location_id = _seed_ai_data(db_session)
    client, fake_responses = _fake_client(
        _response([SimpleNamespace(type="message")], "Which date do you mean?")
    )

    result = _run(db_session, client, location_id, "How did we do?")

    assert result.answer == "Which date do you mean?"
    assert result.tool_calls_used == []
    assert len(fake_responses.calls) == 1


def test_unknown_tool_name_is_rejected(
    db_session: Session,
) -> None:
    location_id = _seed_ai_data(db_session)
    client, _ = _fake_client(
        _response([_function_call("execute_sql", "{}", "call-invalid")])
    )

    with pytest.raises(AIAnalystInvalidToolCallError, match="unsupported"):
        _run(db_session, client, location_id)


@pytest.mark.parametrize(
    "arguments",
    [
        "{not-json",
        '{"review_date":"not-a-date"}',
        '{"review_date":"2026-09-12","unexpected":true}',
        "[]",
    ],
)
def test_malformed_tool_arguments_are_rejected(
    db_session: Session,
    arguments: str,
) -> None:
    location_id = _seed_ai_data(db_session)
    client, _ = _fake_client(
        _response(
            [_function_call("get_daily_summary", arguments, "call-invalid-args")]
        )
    )

    with pytest.raises(AIAnalystInvalidToolCallError):
        _run(db_session, client, location_id)


def test_nonexistent_location_is_rejected_before_any_model_call(
    db_session: Session,
) -> None:
    client, fake_responses = _fake_client(
        _response([SimpleNamespace(type="message")], "An unsupported answer.")
    )

    with pytest.raises(LocationNotFoundError, match="Location not found"):
        _run(db_session, client, 999)

    assert fake_responses.calls == []


def test_missing_api_key_returns_safe_configuration_error(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_MODEL", "test-model")

    with pytest.raises(AIAnalystConfigurationError, match="OPENAI_API_KEY"):
        run_ai_analyst_query(db_session, 1, "Question")


def test_missing_model_configuration_fails_without_guessing_a_model(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.delenv("OPENAI_MODEL", raising=False)

    with pytest.raises(AIAnalystConfigurationError, match="OPENAI_MODEL"):
        run_ai_analyst_query(db_session, 1, "Question")


def test_function_call_outputs_keep_matching_call_ids(
    db_session: Session,
) -> None:
    location_id = _seed_ai_data(db_session)
    client, fake_responses = _fake_client(
        _response(
            [
                _function_call(
                    "get_daily_summary",
                    '{"review_date":"2026-09-12"}',
                    "call-id-preserved",
                )
            ]
        ),
        _response([SimpleNamespace(type="message")], "Done."),
    )

    _run(db_session, client, location_id)

    output = fake_responses.calls[1]["input"][-1]
    assert output["type"] == "function_call_output"
    assert output["call_id"] == "call-id-preserved"
    assert json.loads(output["output"])["order_total_amount"] == 972


def test_repeated_tool_calls_stop_at_iteration_limit(
    db_session: Session,
) -> None:
    location_id = _seed_ai_data(db_session)
    responses = [
        _response(
            [
                _function_call(
                    "get_daily_summary",
                    '{"review_date":"2026-09-12"}',
                    f"call-{index}",
                )
            ]
        )
        for index in range(MAX_TOOL_CALL_ITERATIONS)
    ]
    client, fake_responses = _fake_client(*responses)

    with pytest.raises(AIAnalystToolLimitError, match="maximum"):
        _run(db_session, client, location_id)

    assert len(fake_responses.calls) == MAX_TOOL_CALL_ITERATIONS


def test_endpoint_returns_404_for_nonexistent_tool_location(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services import ai_analyst

    fake_client, _ = _fake_client(
        _response(
            [
                _function_call(
                    "get_daily_summary",
                    '{"review_date":"2026-09-12"}',
                    "call-not-found",
                )
            ]
        )
    )
    monkeypatch.setattr(
        ai_analyst,
        "_create_openai_client",
        lambda: (fake_client, "test-model"),
    )

    response = client.post(
        "/api/ai-analyst/query",
        json={"question": "Summarize September 12, 2026.", "location_id": 999},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Location not found."}


def test_endpoint_reports_missing_api_key_without_leaking_configuration(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_MODEL", "test-model")

    response = client.post(
        "/api/ai-analyst/query",
        json={"question": "Summarize September 12, 2026.", "location_id": 1},
    )

    assert response.status_code == 503
    assert response.json() == {
        "detail": "AI analyst is not configured: OPENAI_API_KEY is missing."
    }
    assert "test-key" not in response.text


def test_endpoint_does_not_echo_or_use_secrets_in_request_body(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_MODEL", "test-model")
    response = client.post(
        "/api/ai-analyst/query",
        json={
            "question": "Summarize September 12, 2026.",
            "location_id": 1,
            "api_key": "must-not-be-accepted",
        },
    )

    assert response.status_code == 503
    assert "OPENAI_API_KEY" in response.text
    assert "must-not-be-accepted" not in response.text


def test_endpoint_maps_provider_errors_without_exposing_details(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    location_id = client.post(
        "/api/locations",
        json={"name": "Provider Error Location"},
    ).json()["id"]

    class FailingResponses:
        def create(self, **kwargs: object) -> object:
            raise RuntimeError("sensitive provider response details")

    monkeypatch.setattr(
        "app.services.ai_analyst._create_openai_client",
        lambda: (SimpleNamespace(responses=FailingResponses()), "test-model"),
    )

    response = client.post(
        "/api/ai-analyst/query",
        json={"question": "Summarize September 12, 2026.", "location_id": location_id},
    )

    assert response.status_code == 502
    assert "sensitive provider response details" not in response.text


def test_endpoint_sanitizes_ledger_tool_execution_errors(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    location_id = client.post(
        "/api/locations",
        json={"name": "Tool Failure Location"},
    ).json()["id"]
    fake_client, _ = _fake_client(
        _response(
            [
                _function_call(
                    "get_daily_summary",
                    '{"review_date":"2026-09-12"}',
                    "call-tool-failure",
                )
            ]
        )
    )
    monkeypatch.setattr(
        "app.services.ai_analyst._create_openai_client",
        lambda: (fake_client, "test-model"),
    )
    monkeypatch.setattr(
        "app.services.analyst.get_daily_summary",
        lambda *args: (_ for _ in ()).throw(
            RuntimeError("sensitive database failure")
        ),
    )

    response = client.post(
        "/api/ai-analyst/query",
        json={"question": "Summarize September 12, 2026.", "location_id": location_id},
    )

    assert response.status_code == 500
    assert "sensitive database failure" not in response.text


def test_ai_query_does_not_mutate_ledger(
    db_session: Session,
) -> None:
    location_id = _seed_ai_data(db_session)
    before = {
        model.__tablename__: db_session.scalar(
            select(func.count()).select_from(model)
        )
        for model in (models.Order, models.OrderLineItem, models.Payment, models.Refund)
    }
    client, _ = _fake_client(
        _response(
            [
                _function_call(
                    "get_daily_summary",
                    '{"review_date":"2026-09-12"}',
                    "call-read-only",
                )
            ]
        ),
        _response([SimpleNamespace(type="message")], "Sales were $9.72."),
    )

    _run(db_session, client, location_id)

    after = {
        model.__tablename__: db_session.scalar(
            select(func.count()).select_from(model)
        )
        for model in (models.Order, models.OrderLineItem, models.Payment, models.Refund)
    }
    assert after == before


def test_tool_definitions_do_not_allow_model_to_choose_location_id(
    db_session: Session,
) -> None:
    location_id = _seed_ai_data(db_session)
    client, fake_responses = _fake_client(
        _response([SimpleNamespace(type="message")], "Please provide a date.")
    )

    _run(db_session, client, location_id)

    tool_definitions = fake_responses.calls[0]["tools"]
    assert {tool["name"] for tool in tool_definitions} == {
        "get_daily_summary",
        "get_reconciliation_exceptions",
        "get_top_items",
        "get_refund_summary",
        "get_discount_summary",
        "compare_daily_performance",
    }
    assert all(
        "location_id" not in tool["parameters"]["properties"]
        for tool in tool_definitions
    )
    assert str(location_id) in fake_responses.calls[0]["input"][0]["content"]


def test_provider_failure_does_not_expose_provider_details(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    location_id = _seed_ai_data(db_session)

    class FailingResponses:
        def create(self, **kwargs: object) -> object:
            raise RuntimeError("sensitive provider response details")

    client = SimpleNamespace(responses=FailingResponses())
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_MODEL", "test-model")

    with pytest.raises(AIAnalystProviderError) as captured:
        _run(db_session, client, location_id)

    assert "sensitive provider response details" not in str(captured.value)
