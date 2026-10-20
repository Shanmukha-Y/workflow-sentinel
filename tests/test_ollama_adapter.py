"""Local protocol tests; no real HTTP/inference in unit tests."""

import copy
import unittest

from workflow_sentinel.ollama_adapter import OllamaAdapter

MODEL = "qwen3.8:27b-q4_K_M"


class Client:
    def __init__(self, response=None):
        self.requests = []
        self.response = response or {
            "model": MODEL,
            "done": True,
            "done_reason": "stop",
            "prompt_eval_count": 100,
            "eval_count": 20,
            "total_duration": 1000000,
            "message": {
                "role": "assistant",
                "tool_calls": [{"function": {"name": "evidence", "arguments": {"packet": 0}}}],
            },
        }

    def model_info(self, model):
        return {
            "tag": model,
            "digest": "a" * 64,
            "download_bytes": 18000000000,
            "capabilities": ["tools", "thinking"],
        }

    def call(self, route, body=None, **kwargs):
        if route == "/api/ps":
            return {"models": []}
        self.requests.append((route, copy.deepcopy(body), kwargs))
        return copy.deepcopy(self.response)


class OllamaTests(unittest.TestCase):
    def make(self, client=None):
        return OllamaAdapter(
            client or Client(), model=MODEL, max_output_tokens=256, allow_local_inference=True
        )

    def test_native_roundtrip_and_usage(self):
        client = Client()
        adapter = self.make(client)
        packets = [{"rule_id": "template-injection", "decision": "review"}]
        command = adapter.next(packets, [], 60)
        self.assertEqual(command, {"action": "evidence", "packet": 0})
        client.response["message"]["tool_calls"][0]["function"]["name"] = "propose"
        adapter.next(packets, [{"action": "evidence", "packet": 0, "evidence": []}], 60)
        payload = client.requests[-1][1]
        self.assertEqual(payload["messages"][-1]["role"], "tool")
        self.assertEqual(payload["messages"][-1]["tool_name"], "evidence")
        self.assertFalse(payload["think"])
        self.assertFalse(payload["stream"])
        self.assertEqual(
            payload["options"], {"num_ctx": 8192, "num_predict": 256, "temperature": 0, "seed": 0}
        )
        self.assertEqual(adapter.usage_records[0], {"input_tokens": 100, "output_tokens": 20})
        self.assertEqual(adapter.attempts[0]["status"], "accepted")
        self.assertIn("response_sha256", adapter.attempts[0])

    def test_advertised_tools_follow_host_state(self):
        client = Client()
        adapter = self.make(client)
        packets = [{"rule_id": "template-injection", "decision": "review"}]
        adapter.next(packets, [], 60)
        self.assertEqual(
            {t["function"]["name"] for t in client.requests[0][1]["tools"]}, {"evidence", "abstain"}
        )
        observations = [{"action": "evidence", "packet": 0, "decision": "review", "evidence": []}]
        client.response["message"]["tool_calls"][0]["function"]["name"] = "propose"
        adapter.next(packets, observations, 60)
        observations.append({"action": "propose", "packet": 0, "repair": {"status": "abstain"}})
        client.response["message"]["tool_calls"][0]["function"]["name"] = "finish"
        adapter.next(packets, observations, 60)
        self.assertEqual(
            {t["function"]["name"] for t in client.requests[-1][1]["tools"]}, {"finish", "abstain"}
        )

    def test_failed_validation_has_no_finish_or_retry_advertised(self):
        from workflow_sentinel.agent import available_tools

        packets = [{"rule_id": "template-injection", "decision": "review"}]
        obs = [
            {"packet": 0, "action": "evidence"},
            {"packet": 0, "action": "propose", "repair": {"status": "proposed"}},
        ]
        self.assertEqual(available_tools(packets, obs), {"abstain": [], "validate": [0]})
        obs.append({"packet": 0, "action": "validate", "static_validation": {"status": "rejected"}})
        self.assertEqual(available_tools(packets, obs), {"abstain": []})

    def test_tool_call_id_roundtrip_is_preserved(self):
        client = Client()
        client.response["message"]["tool_calls"][0]["id"] = "call_native123"
        adapter = self.make(client)
        packets = [{"rule_id": "x", "decision": "review"}]
        adapter.next(packets, [], 60)
        client.response["message"]["tool_calls"][0]["function"]["name"] = "propose"
        client.response["message"]["tool_calls"][0]["id"] = "call_second"
        adapter.next(packets, [{"packet": 0, "action": "evidence", "evidence": []}], 60)
        messages = client.requests[-1][1]["messages"]
        self.assertEqual(messages[-1]["tool_call_id"], "call_native123")
        self.assertEqual(messages[-2]["tool_calls"][0]["id"], "call_native123")
