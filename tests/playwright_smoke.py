import os

from playwright.sync_api import sync_playwright


def main() -> None:
  # 简单的 Playwright 端到端检查：
  # - 打开首页
  # - 检查标题文案是否存在
  url = os.environ.get("APP_URL", "http://127.0.0.1:5000/")
  with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto(url, wait_until="networkidle")
    title_text = page.text_content("h1.title") or ""
    assert "音轨提取" in title_text
    browser.close()


if __name__ == "__main__":
  main()
