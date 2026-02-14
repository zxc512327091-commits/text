import argparse
import os
from dataclasses import dataclass


@dataclass
class VoiceAgentConfig:
    openai_model: str = "gpt-4o-mini"
    max_chars: int = 280


class VoiceAgent:
    def __init__(self, config: VoiceAgentConfig | None = None) -> None:
        self.config = config or VoiceAgentConfig()
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("未安装 openai 依赖，请先执行: pip install -r requirements.txt") from exc
        self.openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def build_call_script(self, objective: str, recipient_name: str | None = None) -> str:
        name_context = f"收件人姓名：{recipient_name}" if recipient_name else "收件人姓名：未知"
        prompt = (
            "你是中文电话外呼语音助手。"
            "请基于目标写一段礼貌、自然、简短的中文电话开场白，"
            f"长度不超过 {self.config.max_chars} 字，并在结尾提出一个明确问题。"
            f"\n目标：{objective}\n{name_context}"
        )

        response = self.openai.responses.create(
            model=self.config.openai_model,
            input=[
                {
                    "role": "system",
                    "content": "你是资深中文电话客服文案专家。",
                },
                {"role": "user", "content": prompt},
            ],
        )
        text = response.output_text.strip()
        return text[: self.config.max_chars]


class OfflineVoiceAgent:
    """本地离线文案生成器，便于无 API 凭据时快速联调流程。"""

    def __init__(self, config: VoiceAgentConfig | None = None) -> None:
        self.config = config or VoiceAgentConfig()

    def build_call_script(self, objective: str, recipient_name: str | None = None) -> str:
        target = recipient_name or "您好"
        text = (
            f"{target}，打扰了。我这边来电是想和您确认：{objective}。"
            "现在方便简单沟通一下吗？"
        )
        return text[: self.config.max_chars]


class PhoneCaller:
    def __init__(self) -> None:
        try:
            from twilio.rest import Client as TwilioClient
        except ImportError as exc:
            raise RuntimeError("未安装 twilio 依赖，请先执行: pip install -r requirements.txt") from exc

        self.account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        self.auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        self.from_number = os.getenv("TWILIO_FROM_NUMBER")
        if not all([self.account_sid, self.auth_token, self.from_number]):
            raise RuntimeError(
                "缺少 Twilio 环境变量：TWILIO_ACCOUNT_SID / TWILIO_AUTH_TOKEN / TWILIO_FROM_NUMBER"
            )
        self.client = TwilioClient(self.account_sid, self.auth_token)

    def call(self, to_number: str, script: str) -> str:
        twiml = f"""
<Response>
    <Say language=\"zh-CN\" voice=\"Polly.Zhiyu\">{script}</Say>
    <Pause length=\"1\"/>
    <Say language=\"zh-CN\" voice=\"Polly.Zhiyu\">感谢接听，期待您的回复。</Say>
</Response>
""".strip()
        call = self.client.calls.create(
            to=to_number,
            from_=self.from_number,
            twiml=twiml,
        )
        return call.sid


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="生成中文语音外呼文案并发起电话")
    parser.add_argument("--objective", required=True, help="通话目标，例如：确认明天面试时间")
    parser.add_argument("--to", required=True, help="被叫号码（E.164 格式，如 +8613800000000）")
    parser.add_argument("--name", default=None, help="被叫姓名（可选）")
    parser.add_argument("--dry-run", action="store_true", help="仅生成文案，不实际发起呼叫")
    parser.add_argument(
        "--offline",
        action="store_true",
        help="离线模式：不调用 OpenAI API，使用本地模板生成文案（适合快速测试）",
    )
    return parser.parse_args()


def load_env_file() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv()


def main() -> None:
    load_env_file()
    args = parse_args()

    agent = OfflineVoiceAgent() if args.offline else VoiceAgent()
    script = agent.build_call_script(args.objective, args.name)

    print("=== 生成的语音文案 ===")
    print(script)

    if args.dry_run:
        print("[DRY RUN] 已跳过实际呼叫。")
        return

    caller = PhoneCaller()
    sid = caller.call(args.to, script)
    print(f"呼叫已发起，Call SID: {sid}")


if __name__ == "__main__":
    main()
