import os
import time
from playwright.sync_api import sync_playwright

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        # Catch console errors and logs
        console_messages = []
        page.on("console", lambda msg: console_messages.append(f"[{msg.type.upper()}] {msg.text}"))
        page.on("pageerror", lambda err: console_messages.append(f"[PAGE_ERROR] {err.message}\n{err.stack}"))

        print("Navigating to http://localhost:8000...")
        page.goto("http://localhost:8000")
        page.wait_for_load_state("networkidle")
        time.sleep(2)

        print("\n--- Console Messages on Load ---")
        for msg in console_messages:
            print(msg)
        console_messages.clear()

        # Let's check if we are logged in.
        # If not, let's log in as marton using localStorage injection.
        is_logged_in = page.evaluate("() => localStorage.getItem('cs_current_session') !== null")
        print(f"Logged in status in localStorage: {is_logged_in}")
        
        if not is_logged_in:
            print("Logging in as marton via localStorage...")
            page.evaluate("""() => {
                localStorage.setItem('cs_current_session', JSON.stringify({username: 'marton', role: 'tech'}));
            }""")
            page.reload()
            page.wait_for_load_state("networkidle")
            time.sleep(2)
            print("\n--- Console Messages after reloading ---")
            for msg in console_messages:
                print(msg)
            console_messages.clear()

        # Screenshot of the home page (Scan tab)
        page.screenshot(path="scratch/scan_tab.png")
        print("Saved scratch/scan_tab.png")

        # Let's try to go to the Grades tab
        print("Clicking GRADES tab...")
        page.click("#nb-grades")
        time.sleep(1)
        print("\n--- Console Messages after clicking GRADES ---")
        for msg in console_messages:
            print(msg)
        console_messages.clear()
        page.screenshot(path="scratch/grades_tab.png")
        print("Saved scratch/grades_tab.png")

        # Let's try to go to the History tab
        print("Clicking HISTORY tab...")
        page.click("#nb-history")
        time.sleep(1)
        print("\n--- Console Messages after clicking HISTORY ---")
        for msg in console_messages:
            print(msg)
        console_messages.clear()
        page.screenshot(path="scratch/history_tab.png")
        print("Saved scratch/history_tab.png")

        # Let's try to go to the Prices tab
        print("Clicking PRICES tab...")
        page.click("#nb-prices")
        time.sleep(1)
        print("\n--- Console Messages after clicking PRICES ---")
        for msg in console_messages:
            print(msg)
        console_messages.clear()
        page.screenshot(path="scratch/prices_tab.png")
        print("Saved scratch/prices_tab.png")

        # Let's try to go to the Ref tab
        print("Clicking REF tab...")
        page.click("#nb-ref")
        time.sleep(1)
        print("\n--- Console Messages after clicking REF ---")
        for msg in console_messages:
            print(msg)
        console_messages.clear()
        page.screenshot(path="scratch/ref_tab.png")
        print("Saved scratch/ref_tab.png")

        browser.close()

if __name__ == "__main__":
    run()
