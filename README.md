# 语音智能体外呼脚本

这个项目会先用 OpenAI 生成中文电话外呼文案，再通过 Twilio 发起电话，让系统语音自动播报。

## 1) 安装

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 2) 配置环境变量

```bash
cp .env.example .env
# 编辑 .env，填入你的 OPENAI 与 TWILIO 凭据
```

## 3) 先进行文案生成（不打电话）

```bash
python voice_agent.py \
  --objective "确认您是否能参加明天下午三点的面试" \
  --to "+8613800000000" \
  --name "王先生" \
  --dry-run
```

## 4) 发起实际电话

```bash
python voice_agent.py \
  --objective "确认您是否能参加明天下午三点的面试" \
  --to "+8613800000000" \
  --name "王先生"
```

> 注意：需要可用的 Twilio 号码、账户余额和合规配置。中国大陆外呼请先确认号码能力、地区政策与运营商限制。
