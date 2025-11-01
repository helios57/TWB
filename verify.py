from playwright.sync_api import sync_playwright

def run(playwright):
    browser = playwright.chromium.launch()
    page = browser.new_page()
    page.goto("http://localhost:8080/villages")
    page.screenshot(path="verification.png")
    browser.close()

with sync_playwright() as playwright:
    run(playwright)
