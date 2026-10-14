"""OFFLINE proposal helpers only. No sender, CLI, credential access or activation.

Existing native responses, jobs, ledgers and quota events are never rewritten.
An approved future adapter must persist returned sidecar state before continuing.
"""
import copy

from agents.call_telemetry import BudgetStopped

MODEL = 'gemma-4-31b-it'
RESERVE = 4096
LIMIT = 5
WINDOW = 61
TOTAL_TPM = 16000
LABEL = 'usage missing; conservative reserve booked'


def require_calls_allowed(state):
    count = len(state.get('bookings', {}))
    if state.get('missing_usage_count', count) != count:
        raise BudgetStopped('persistent missing-usage counter differs')
    if count > LIMIT or state.get('review_required', False):
        raise BudgetStopped('sixth missing-usage reply retained; owner review required')


def conservative_booking(model, response, counted_prompt, maximum=RESERVE):
    """Describe a booking, never manufacture native usage or repair a response."""
    usage = response.get('usageMetadata') or {}
    if 'candidatesTokenCount' in usage:
        return None  # The unchanged strict validator handles present usage.
    if model != MODEL or response.get('modelVersion') != MODEL or maximum != RESERVE:
        raise BudgetStopped('missing usage exemption is Gemma-only/exact identity/4096')
    prompt = usage.get('promptTokenCount')
    thoughts = usage.get('thoughtsTokenCount', 0)
    cached = usage.get('cachedContentTokenCount', 0)
    total = usage.get('totalTokenCount')
    if (type(counted_prompt) is not int or counted_prompt < 0 or
            any(type(x) is not int or x < 0 for x in (prompt, thoughts, cached)) or
            prompt > counted_prompt + 128 or cached > prompt or thoughts > RESERVE or
            counted_prompt + 128 + RESERVE > TOTAL_TPM):
        raise BudgetStopped('independent prompt/context/cache/thought guard remains')
    if total is not None and (type(total) is not int or
                              not prompt + thoughts <= total <= prompt + RESERVE):
        raise BudgetStopped('inconsistent reported total remains a guard')
    if not response.get('candidates') or not response.get('responseId'):
        raise BudgetStopped('missing native candidate/response identity remains a guard')
    return dict(label=LABEL, output_tokens_booked=RESERVE,
                output_tokens_native=None, prompt_tokens_native=prompt,
                thoughts_included_in_reserve=True, native_response_unchanged=True,
                no_resend=True)


def book_once(state, attempt_id, booking):
    """Return a durable-sidecar candidate; the sixth is recorded BEFORE stopping."""
    new = copy.deepcopy(state)
    entries = new.setdefault('bookings', {})
    if attempt_id in entries:
        if entries[attempt_id] != booking:
            raise BudgetStopped('conflicting usage booking')
    else:
        entries[attempt_id] = copy.deepcopy(booking)
    new['missing_usage_count'] = len(entries)
    new['review_required'] = len(entries) > LIMIT
    return new


def combined_ready_at(events, counted_prompt, now):
    """Additional prospective TOTAL input+output reservation; old limits stay.

Every generation attempt (including retries) reserves prompt+128+4096 BEFORE
send, even when its eventual usage is present. No early discount. Existing
24 HTTP / 14,400 input / daily / provider-reset guards run independently.
"""
    if type(counted_prompt) is not int or not 0 <= counted_prompt <= 11776:
        raise BudgetStopped('unchanged exact combined context guard')
    needed = counted_prompt + 128 + RESERVE
    active = sorted((e for e in events if e['at'] > now - WINDOW),
                    key=lambda e: e['at'])
    if any(e['at'] > now or type(e['tokens']) is not int or e['tokens'] < 0
           for e in active):
        raise BudgetStopped('invalid combined pacing history')
    used = sum(e['tokens'] for e in active)
    ready = now
    for event in active:
        if used + needed <= TOTAL_TPM:
            break
        used -= event['tokens']
        ready = max(ready, event['at'] + WINDOW)
    return ready


def reserve_combined(events, counted_prompt, now, attempt_id):
    ready = combined_ready_at(events, counted_prompt, now)
    if ready > now:
        raise BudgetStopped('combined pacing wait required until %.6f' % ready)
    if any(e['attempt_id'] == attempt_id for e in events):
        raise BudgetStopped('duplicate combined reservation')
    return events + [dict(at=now, tokens=counted_prompt + 128 + RESERVE,
                          attempt_id=attempt_id)]
