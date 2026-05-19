from playwright.sync_api import sync_playwright

DEFAULT_URL = "https://outlook.office.com/mail/"


def open_outlook_web(url=DEFAULT_URL, headless=True):
    p = sync_playwright().start()
    browser = p.chromium.launch(headless=headless)
    page = browser.new_page()
    page.goto(url)
    return p, browser, page


def read_inbox_web(page, limit=10):
    page.wait_for_selector('[role="listitem"]', timeout=10000)
    items = page.query_selector_all('[role="listitem"]')[:limit]
    results = []
    for item in items:
        subject = item.query_selector('[aria-label*="Subject"]')
        sender = item.query_selector('[aria-label*="From"]')
        preview = item.query_selector('[aria-label*="Preview"]')
        results.append({
            "subject": subject.inner_text() if subject else "",
            "from": sender.inner_text() if sender else "",
            "preview": preview.inner_text() if preview else ""
        })
    return results


def search_web(page, keyword):
    search_box = page.query_selector('[aria-label="Search"]')
    if search_box:
        search_box.fill(keyword)
        search_box.press("Enter")
        page.wait_for_load_state("networkidle")
        return read_inbox_web(page)
    return []


def send_email_web(page, to, subject, body):
    page.click('[aria-label="New mail"]')
    page.fill('[aria-label="To"]', to)
    page.fill('[aria-label="Subject"]', subject)
    page.fill('[aria-label="Message body"]', body)
    page.click('[aria-label="Send"]')
    return True
