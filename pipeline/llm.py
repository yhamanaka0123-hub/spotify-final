"""Claude JSON helper used by the verify, group and memo roles (logs every attempt)."""
import json
import time

from pipeline.runtime import BudgetExceeded

PRICES = {"claude-haiku-5-5": (1e-7, 5e-7), "claude-sonnet-5-5": (2e-6, 1e-5)}  # reservation only


def claude_json(run, *, role, model, system, user, schema, review_ids, label_config, max_tokens,
                effort="low", **extra):
    """One structured-output request. Returns (parsed_json, call_record). Invalid output is
    retried once; a failure after that raises after logging."""
    import anthropic
    client = anthropic.Anthropic(max_retries=3)
    pin, pout = PRICES[model]
    reserve = (len(system) + len(user)) / 2 * pin + max_tokens * pout
    last = None
    for attempt in (1, 2):
        run.reserve(reserve)
        started, actual = time.time(), 0.0
        try:
            # Haiku: thinking off (allowed at effort <= high) so the output budget goes to the answer.
            thinking = {"thinking": {"type": "disabled"}} if model.startswith("claude-haiku") else {}
            msg = client.messages.create(
                model=model, max_tokens=max_tokens, system=system, **thinking,
                output_config={"effort": effort, "format": {"type": "json_schema", "schema": schema}},
                messages=[{"role": "user", "content": user}])
            if msg.stop_reason != "end_turn":
                raise ValueError(f"stop_reason={msg.stop_reason}")
            data = json.loads(next(b.text for b in msg.content if b.type == "text"))
            rec = run.log_call(role=role, model=model, review_ids=review_ids, outcome="succeeded",
                               label_config=label_config, input_tokens=msg.usage.input_tokens,
                               output_tokens=msg.usage.output_tokens, started=started,
                               request_id=msg._request_id, attempt=attempt, **extra)
            actual = rec["cost_usd"]
            return data, rec
        except BudgetExceeded:
            raise
        except Exception as e:
            last = e
            run.log_call(role=role, model=model, review_ids=review_ids, outcome="failed", label_config=label_config,
                         input_tokens=None, output_tokens=None, started=started, attempt=attempt,
                         error=f"{type(e).__name__}: {e}", **extra)
        finally:
            run.settle(reserve, actual)
    raise RuntimeError(f"{role} failed after retry: {last}")
