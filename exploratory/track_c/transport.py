"""Receipt-gated transport support and append-only accounting."""
import base64
import hashlib
import http.client
import json
import os
import re
import subprocess
import time

from .protocol import MODELS, ROOT

# Integer units of one ten-millionth of a dollar.
RATES = dict(zip(MODELS, [(1, 5), (20, 100)]))
CAPS = dict(zip((*MODELS, "total"), [1, 8, 9]))
RETRY_STATUS = {429, 500, 502, 503, 504, 529}
WAITS = (10, 30, 60, 120)


class Stop(Exception):
    """A retained run guard or transport stop."""


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT).strip()


def validate_receipt(receipt, raw_cases, output_name):
    commit = git("rev-parse", "HEAD").decode("ascii")
    if not re.fullmatch(r"[0-9a-f]{40}", commit) or git("status", "--porcelain"):
        raise Stop("paid launch requires a clean exact commit")
    expected = {
        "approved_by": "Chris Lahn",
        "commit": commit,
        "cases_sha256": hashlib.sha256(raw_cases).hexdigest(),
        "models": list(MODELS),
        "caps_dollars": CAPS,
        "output": output_name,
    }
    if json.dumps(receipt, sort_keys=True) != json.dumps(expected, sort_keys=True):
        raise Stop("owner receipt does not match this launch")


class Journal:
    def __init__(self, path):
        self.path = path

    def __call__(self, event, **fields):
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(dict(event=event, **fields)) + "\n")
            handle.flush()
            os.fsync(handle.fileno())


def encode(body):
    return json.dumps(body, ensure_ascii=False).encode("utf-8")


def exchange(payload, key):
    """Only retry before a response, or after a complete structured HTTP error."""
    connection = http.client.HTTPSConnection("api.anthropic.com", timeout=120)
    status = None
    raw = bytearray()
    try:
        connection.request("POST", "/v1/messages", body=payload, headers={
            "content-type": "application/json", "anthropic-version": "2023-06-01",
            "x-api-key": key,
        })
        response = connection.getresponse()
        status = response.status
        while chunk := response.read1(65_536):
            raw.extend(chunk)
        if response.length not in (None, 0):
            return status, bytes(raw), "partial_response"
        return status, bytes(raw), None
    except http.client.IncompleteRead as error:
        return status, bytes(raw) + error.partial, "partial_response"
    except (OSError, http.client.RemoteDisconnected):
        return status, bytes(raw), "connection_failure" if status is None else "response_read_failure"
    except http.client.HTTPException:
        return status, bytes(raw), "http_protocol_failure"
    finally:
        connection.close()


def token_bound(body, payload):
    # Allow one token per serialized byte and 16K tokens for provider framing.
    # Signatures can also restore the full thinking from each prior response.
    prior_replies = sum(message["role"] == "assistant" for message in body["messages"])
    # Decline payloads whose bound reaches the higher Haiku pricing tier.
    bound = len(payload) + 16_384 + prior_replies * body["max_tokens"]
    if bound >= 100_000:
        raise Stop("input bound exceeds the approved pricing tier")
    return bound


def ordinary_http_error(data):
    return (isinstance(data, dict) and set(data) <= {"type", "error", "request_id"}
            and data.get("type") == "error" and isinstance(data.get("error"), dict))


class Client:
    def __init__(self, key, log, send=exchange, sleep=time.sleep):
        self.key = key
        self.log = log
        self.send = send
        self.sleep = sleep
        self.booked = dict.fromkeys(MODELS, 0)

    def __call__(self, body, **location):
        model = body["model"]
        payload = encode(body)
        maximum_input = token_bound(body, payload)
        input_rate, output_rate = RATES[model]
        reserve = maximum_input * 2 * input_rate + body["max_tokens"] * output_rate
        for attempt in range(1, 6):
            if (self.booked[model] + reserve >= CAPS[model] * 10_000_000
                    or sum(self.booked.values()) + reserve >= CAPS["total"] * 10_000_000):
                raise Stop("budget cap")
            self.booked[model] += reserve
            self.log("request", **location, attempt=attempt, body=body, reserved_units=reserve)
            status, raw, error = self.send(payload, self.key)
            self.log("response", **location, attempt=attempt, status=status, error=error,
                     raw_base64=base64.b64encode(raw).decode("ascii"))
            try:
                data = json.loads(raw)
            except (ValueError, UnicodeError):
                data = None
            if status == 200 and error is None:
                if not isinstance(data, dict):
                    raise Stop("invalid response")
                usage = data.get("usage")
                self.log("usage", **location, attempt=attempt, usage=usage)
                charged = self.charge(data, model, maximum_input, body["max_tokens"])
                self.booked[model] += charged - reserve
                self.log("settlement", **location, attempt=attempt, charged_units=charged)
                return data
            retry = ((status is None and error == "connection_failure" and not raw)
                     or (status in RETRY_STATUS and error is None
                         and (not raw or ordinary_http_error(data))))
            if not retry or attempt == 5:
                raise Stop(error or f"HTTP {status} after {attempt} attempt(s)")
            wait = WAITS[attempt - 1]
            self.log("retry", **location, attempt=attempt, wait_seconds=wait)
            self.sleep(wait)
        raise AssertionError("unreachable")

    @staticmethod
    def charge(data, model, max_input, max_output):
        if data.get("model") != model:
            raise Stop("unexpected model identity")
        usage = data.get("usage")
        if not isinstance(usage, dict):
            raise Stop("missing usage")
        counts = [usage.get("input_tokens"), usage.get("output_tokens"),
                  usage.get("cache_read_input_tokens", 0), usage.get("cache_creation_input_tokens", 0)]
        if any(type(value) is not int or value < 0 for value in counts):
            raise Stop("invalid usage")
        billed_input, output, cache_read, cache_creation = counts
        if billed_input + cache_read + cache_creation > max_input or output > max_output:
            raise Stop("usage exceeded reservation assumptions")
        input_rate, output_rate = RATES[model]
        # Budget at full price for reads and the higher cache-write multiplier.
        return (billed_input + cache_read + 2 * cache_creation) * input_rate + output * output_rate
