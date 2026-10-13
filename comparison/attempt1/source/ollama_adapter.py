"""Local-only Ollama tool adapter; fixed loopback HTTP, no proxy, redirects or credentials."""
from __future__ import annotations

import json
import hashlib
import re
import time
from typing import Any
from urllib import request as http

from workflow_sentinel.agent import available_tools, decode, request
from workflow_sentinel.openai_adapter import INSTRUCTIONS, ProviderError, deadline, tools

BASE = 'http://127.0.0.1:11434'
MAX_BYTES = 16000
MAX_INPUT = 64000
CONTEXT = 8192


class NoRedirect(http.HTTPRedirectHandler):
    def redirect_request(self, req: Any, fp: Any, code: int, msg: str,
                         headers: Any, newurl: str) -> None:
        raise ProviderError('Local redirect refused')


class OllamaClient:
    """Connect only to the existing loopback daemon; never pull/start/configure a server."""
    def __init__(self) -> None:
        self.opener = http.build_opener(http.ProxyHandler({}), NoRedirect())

    def call(self, route: str, body: dict[str, Any] | None = None,
             timeout: float = 15, limit: int = MAX_BYTES) -> dict[str, Any]:
        if route not in {'/api/chat', '/api/generate', '/api/show', '/api/tags', '/api/version', '/api/ps'}:
            raise ProviderError('Local route refused')
        req = http.Request(BASE + route, data=json.dumps(body).encode() if body else None,
                           headers={'Content-Type': 'application/json'})
        with self.opener.open(req, timeout=timeout) as response:
            raw = response.read(limit + 1)
        if len(raw) > limit:
            raise ProviderError('Local response size exceeded')
        doc = decode(raw)
        if not isinstance(doc, dict):
            raise ProviderError('Local response shape refused')
        return doc

    def model_info(self, model: str) -> dict[str, Any]:
        tags = self.call('/api/tags', limit=1000000)
        found = next((m for m in tags.get('models', []) if m.get('name') == model), None)
        if (not found or type(found.get('size')) is not int or found['size'] <= 0
                or not re.fullmatch(r'[a-f0-9]{64}', found.get('digest', ''))):
            raise ProviderError('Model must already be installed locally')
        shown = self.call('/api/show', {'model': model}, limit=1000000)
        if (shown.get('remote_host') or shown.get('remote_model')
                or shown.get('details', {}).get('format') != 'gguf'
                or 'tools' not in shown.get('capabilities', [])):
            raise ProviderError('Local GGUF tool-capable model required')
        return {'tag': model, 'digest': found['digest'], 'download_bytes': found['size'],
                'details': found.get('details', {}), 'capabilities': shown['capabilities']}

    def close(self) -> None:
        pass


class OllamaAdapter:
    mode = 'ollama-local-advisory'

    def __init__(self, client: Any, *, model: str, max_output_tokens: int,
                 allow_local_inference: bool = False, capture_raw_evidence: bool = False) -> None:
        if allow_local_inference is not True:
            raise ProviderError('Local inference opt-in required')
        if (not isinstance(model, str) or not re.fullmatch(r'(?:qwen[0-9.]+|gemma[0-9.]+|mistral-small[0-9.]+):[A-Za-z0-9_.-]+', model)
                or 'cloud' in model.lower()):
            raise ProviderError('Explicit supported local model tag required')
        if type(max_output_tokens) is not int or not 64 <= max_output_tokens <= 256:
            raise ProviderError('Local output cap refused')
        self.client, self.model = client, model
        self.capture_raw_evidence = capture_raw_evidence
        self.max_output_tokens = max_output_tokens
        self.model_metadata = client.model_info(model)
        self.history: list[dict[str, Any]] = []
        self.pending: str | None = None
        self.consumed = 0
        self.calls = 0
        self.usage_records: list[dict[str, int] | None] = []
        self.attempts: list[dict[str, Any]] = []

    def next(self, packets: list[dict[str, Any]], observations: list[dict[str, Any]],
             remaining: float) -> dict[str, Any]:
        if self.calls >= 8:
            raise ProviderError('Local request budget exhausted')
        if not self.history:
            manifest = [{'packet': i, 'rule_id': p['rule_id'][:200], 'decision': p['decision']}
                        for i, p in enumerate(packets)]
            self.history = [{'role': 'system', 'content': INSTRUCTIONS},
                            {'role': 'user', 'content': json.dumps({'packets': manifest})}]
        elif self.pending:
            if len(observations) != self.consumed + 1:
                raise ProviderError('Missing local tool observation')
            self.history.append({'role': 'tool', 'tool_name': self.pending,
                                 'content': json.dumps(observations[-1], ensure_ascii=True)})
            self.consumed = len(observations)
            self.pending = None
        permitted = available_tools(packets, observations)
        native_tools = []
        for tool in tools():
            if tool['name'] not in permitted:
                continue
            parameters = tool['parameters']
            if tool['name'] != 'abstain':
                parameters['properties']['packet']['enum'] = permitted[tool['name']]
            native_tools.append({'type': 'function', 'function': {
                'name': tool['name'], 'description': tool['description'],
                'parameters': parameters}})
        body = {'model': self.model, 'messages': self.history, 'tools': native_tools,
                'stream': False, 'keep_alive': '2m',
                'options': {'num_ctx': CONTEXT, 'num_predict': self.max_output_tokens,
                            'temperature': 0, 'seed': 0}}
        if 'thinking' in self.model_metadata.get('capabilities', []):
            body['think'] = False
        if len(json.dumps(body).encode()) > MAX_INPUT:
            raise ProviderError('Local request input budget exhausted')
        self.calls += 1
        self.usage_records.append(None)
        attempt: dict[str, Any] = {'turn': self.calls - 1, 'status': 'error'}
        if self.capture_raw_evidence:
            attempt['raw_request'] = json.loads(json.dumps(body))
        self.attempts.append(attempt)
        started = time.monotonic()
        stage = 'transport'
        try:
            with deadline(min(15.0, remaining)):
                doc = self.client.call('/api/chat', body, timeout=min(15.0, remaining))
            if self.capture_raw_evidence:
                attempt['raw_response'] = doc
            attempt['response_sha256'] = hashlib.sha256(
                json.dumps(doc, sort_keys=True).encode()).hexdigest()
            stage = 'completion'
            for key in ['prompt_eval_count', 'eval_count', 'total_duration', 'load_duration',
                        'prompt_eval_duration', 'eval_duration']:
                if type(doc.get(key)) is int and doc[key] >= 0:
                    attempt[key] = doc[key]
            if (type(doc.get('prompt_eval_count')) is int and type(doc.get('eval_count')) is int
                    and doc['prompt_eval_count'] >= 0 and doc['eval_count'] >= 0):
                self.usage_records[-1] = {'input_tokens': doc['prompt_eval_count'],
                                          'output_tokens': doc['eval_count']}
            if (doc.get('done') is not True or doc.get('done_reason') != 'stop'
                    or doc.get('model') != self.model
                    or doc.get('eval_count', 0) > self.max_output_tokens
                    or doc.get('prompt_eval_count', 0) >= CONTEXT):
                raise ProviderError('Incomplete, oversized or unexpected local response')
            stage = 'tool-count'
            message = doc.get('message', {})
            calls = message.get('tool_calls', [])
            attempt['returned_tool_count'] = len(calls) if isinstance(calls, list) else None
            if message.get('role') != 'assistant' or not isinstance(calls, list) or len(calls) != 1:
                raise ProviderError('Exactly one local tool call required')
            stage = 'arguments'
            function = calls[0].get('function', {})
            args = function.get('arguments')
            if not isinstance(args, dict) or 'action' in args:
                raise ProviderError('Invalid local tool arguments')
            command = request({'action': function.get('name'), **args}, len(packets))
            stage = 'prerequisites'
            if (command['action'] not in permitted or command['action'] != 'abstain'
                    and command['packet'] not in permitted[command['action']]):
                raise ProviderError('Local tool prerequisite refused')
            self.pending = command['action']
            self.history.append({'role': 'assistant', 'content': '', 'tool_calls': [
                {'function': {'name': self.pending, 'arguments': args}}]})
            attempt['status'] = 'accepted'
            attempt['action'] = self.pending
            if 'packet' in command:
                attempt['packet'] = command['packet']
            return command
        except Exception:
            attempt['failure_stage'] = stage
            raise ProviderError('Local request failed or protocol refused') from None
        finally:
            attempt['wall_seconds'] = round(time.monotonic() - started, 6)
            try:
                running = self.client.call('/api/ps').get('models', [])
                selected = next((m for m in running if m.get('name') == self.model), None)
                if selected and type(selected.get('size_vram')) is int:
                    attempt['sampled_model_memory_bytes'] = selected['size_vram']
            except Exception:
                attempt['memory_sample_unavailable'] = True
