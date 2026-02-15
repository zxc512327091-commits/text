import unittest

from web_preview import render_page


class WebPreviewTests(unittest.TestCase):
    def test_render_page_title(self):
        html = render_page()
        self.assertIn("语音智能体预览界面", html)
        self.assertIn("仅预览文案", html)

    def test_render_page_result(self):
        html = render_page(script="测试话术", message="呼叫已发起。", success=True, call_sid="CA123")
        self.assertIn("测试话术", html)
        self.assertIn("CA123", html)
        self.assertIn("呼叫已发起。", html)


if __name__ == "__main__":
    unittest.main()
