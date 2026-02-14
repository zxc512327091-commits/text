import os
import sys
import types
import unittest
from types import SimpleNamespace


class VoiceAgentTests(unittest.TestCase):
    def test_voice_agent_truncates_response(self):
        fake_openai = types.ModuleType("openai")

        class FakeOpenAI:
            def __init__(self, api_key=None):
                self.responses = SimpleNamespace(
                    create=lambda **kwargs: SimpleNamespace(output_text="A" * 500)
                )

        fake_openai.OpenAI = FakeOpenAI
        sys.modules["openai"] = fake_openai

        from voice_agent import VoiceAgent, VoiceAgentConfig

        agent = VoiceAgent(VoiceAgentConfig(max_chars=10))
        text = agent.build_call_script("测试目标", "张三")
        self.assertEqual(text, "A" * 10)

    def test_offline_agent_generates_script(self):
        from voice_agent import OfflineVoiceAgent, VoiceAgentConfig

        agent = OfflineVoiceAgent(VoiceAgentConfig(max_chars=50))
        text = agent.build_call_script("确认明天会议时间", "王先生")
        self.assertIn("确认明天会议时间", text)
        self.assertIn("王先生", text)


class PhoneCallerTests(unittest.TestCase):
    def test_phone_caller_places_call(self):
        fake_twilio_rest = types.ModuleType("twilio.rest")
        captured = {}

        class FakeCalls:
            def create(self, **kwargs):
                captured.update(kwargs)
                return SimpleNamespace(sid="CA123")

        class FakeTwilioClient:
            def __init__(self, sid, token):
                self.calls = FakeCalls()

        fake_twilio_rest.Client = FakeTwilioClient
        sys.modules["twilio.rest"] = fake_twilio_rest

        os.environ["TWILIO_ACCOUNT_SID"] = "sid"
        os.environ["TWILIO_AUTH_TOKEN"] = "token"
        os.environ["TWILIO_FROM_NUMBER"] = "+10000000000"

        from voice_agent import PhoneCaller

        caller = PhoneCaller()
        sid = caller.call("+8613800000000", "您好，这里是测试电话")
        self.assertEqual(sid, "CA123")
        self.assertIn("您好，这里是测试电话", captured["twiml"])


if __name__ == "__main__":
    unittest.main()
