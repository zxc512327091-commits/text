from __future__ import annotations

import html
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs

from voice_agent import OfflineVoiceAgent, PhoneCaller, VoiceAgent


def render_page(
    *,
    objective: str = "",
    name: str = "",
    to_number: str = "",
    mode: str = "offline",
    script: str | None = None,
    message: str | None = None,
    success: bool | None = None,
    error: str | None = None,
    call_sid: str | None = None,
) -> str:
    esc = html.escape
    selected_offline = "selected" if mode != "online" else ""
    selected_online = "selected" if mode == "online" else ""

    alert_html = ""
    if error:
        alert_html += f'<div class="alert error">{esc(error)}</div>'
    if message:
        cls = "ok" if success else "error"
        alert_html += f'<div class="alert {cls}">{esc(message)}</div>'

    result_html = ""
    if script:
        sid_html = f'<p>Call SID: <span class="mono">{esc(call_sid or "")}</span></p>' if call_sid else ""
        result_html = f"""
        <section class=\"result\">
          <h3>生成的话术</h3>
          <p>{esc(script)}</p>
          {sid_html}
        </section>
        """

    return f"""<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>语音智能体预览界面</title>
    <style>
      body {{ font-family: Arial, sans-serif; margin: 24px; background: #f6f8fb; }}
      .card {{ max-width: 760px; margin: 0 auto; background: #fff; border-radius: 12px; padding: 20px; box-shadow: 0 6px 24px rgba(30, 50, 80, 0.08); }}
      h1 {{ margin-top: 0; font-size: 24px; }}
      label {{ display: block; margin: 12px 0 6px; font-weight: 600; }}
      input, textarea, select {{ width: 100%; box-sizing: border-box; padding: 10px; border: 1px solid #ccd3df; border-radius: 8px; font-size: 14px; }}
      textarea {{ min-height: 90px; }}
      .row {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }}
      .actions {{ display: flex; gap: 10px; margin-top: 14px; }}
      button {{ border: 0; border-radius: 8px; padding: 10px 14px; font-weight: 700; cursor: pointer; }}
      .preview {{ background: #2b6ce5; color: #fff; }}
      .call {{ background: #0d9f6e; color: #fff; }}
      .alert {{ margin-top: 14px; padding: 10px 12px; border-radius: 8px; }}
      .error {{ background: #fee2e2; color: #b91c1c; }}
      .ok {{ background: #dcfce7; color: #166534; }}
      .result {{ margin-top: 16px; background: #f2f6ff; border-radius: 8px; padding: 12px; }}
      .mono {{ font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }}
    </style>
  </head>
  <body>
    <main class="card">
      <h1>语音智能体预览界面</h1>
      <p>先生成话术再决定是否呼叫。建议先使用离线模式预览。</p>

      <form method="post" action="/generate">
        <label for="objective">通话目标</label>
        <textarea id="objective" name="objective" placeholder="例如：确认您是否能参加明天下午三点面试">{esc(objective)}</textarea>

        <div class="row">
          <div>
            <label for="name">被叫姓名（可选）</label>
            <input id="name" name="name" value="{esc(name)}" placeholder="例如：王先生" />
          </div>
          <div>
            <label for="to">被叫号码（E.164）</label>
            <input id="to" name="to" value="{esc(to_number)}" placeholder="+8613800000000" />
          </div>
        </div>

        <label for="mode">生成模式</label>
        <select id="mode" name="mode">
          <option value="offline" {selected_offline}>离线模式（不调用 OpenAI）</option>
          <option value="online" {selected_online}>在线模式（调用 OpenAI）</option>
        </select>

        <div class="actions">
          <button class="preview" type="submit" name="action" value="preview">仅预览文案</button>
          <button class="call" type="submit" name="action" value="call">生成并发起呼叫</button>
        </div>
      </form>

      {alert_html}
      {result_html}
    </main>
  </body>
</html>
"""


class PreviewHandler(BaseHTTPRequestHandler):
    def _send_html(self, content: str) -> None:
        data = content.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):  # noqa: N802
        if self.path != "/":
            self.send_error(404)
            return
        self._send_html(render_page())

    def do_POST(self):  # noqa: N802
        if self.path != "/generate":
            self.send_error(404)
            return

        content_length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(content_length).decode("utf-8")
        form = {k: v[0] for k, v in parse_qs(raw).items()}

        objective = form.get("objective", "").strip()
        to_number = form.get("to", "").strip()
        name = form.get("name", "").strip()
        mode = form.get("mode", "offline")
        action = form.get("action", "preview")

        if not objective:
            self._send_html(
                render_page(
                    objective=objective,
                    name=name,
                    to_number=to_number,
                    mode=mode,
                    error="请先填写通话目标。",
                )
            )
            return

        try:
            agent = OfflineVoiceAgent() if mode == "offline" else VoiceAgent()
            script = agent.build_call_script(objective, name or None)
        except Exception as exc:
            self._send_html(
                render_page(
                    objective=objective,
                    name=name,
                    to_number=to_number,
                    mode=mode,
                    error=f"文案生成失败：{exc}",
                )
            )
            return

        message = None
        success = None
        call_sid = None

        if action == "call":
            if not to_number:
                message = "请填写被叫号码后再发起呼叫。"
                success = False
            else:
                try:
                    caller = PhoneCaller()
                    call_sid = caller.call(to_number, script)
                    message = "呼叫已发起。"
                    success = True
                except Exception as exc:
                    message = f"呼叫失败：{exc}"
                    success = False

        self._send_html(
            render_page(
                objective=objective,
                name=name,
                to_number=to_number,
                mode=mode,
                script=script,
                message=message,
                success=success,
                call_sid=call_sid,
            )
        )


def run_server(host: str = "0.0.0.0", port: int = 8000) -> None:
    server = HTTPServer((host, port), PreviewHandler)
    print(f"预览界面已启动: http://127.0.0.1:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run_server()
