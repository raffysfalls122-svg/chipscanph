import time
from playwright.sync_api import sync_playwright

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        page.goto("http://localhost:8000")
        page.wait_for_load_state("networkidle")
        
        # Log in as marton
        page.evaluate("""() => {
            localStorage.setItem('cs_current_session', JSON.stringify({username: 'marton', role: 'tech'}));
        }""")
        page.reload()
        page.wait_for_load_state("networkidle")
        time.sleep(1)

        tabs = ['scan', 'grades', 'prices', 'ref', 'history']
        for tab in tabs:
            page.click(f"#nb-{tab}")
            time.sleep(0.5)
            
            pg_id = f"pg-{tab}"
            
            # Disable animation for testing
            page.evaluate(f"() => {{ document.getElementById('{pg_id}').style.animation = 'none'; }}")
            time.sleep(0.1)

            is_visible = page.evaluate(f"() => window.getComputedStyle(document.getElementById('{pg_id}')).display !== 'none'")
            height = page.evaluate(f"() => document.getElementById('{pg_id}').offsetHeight")
            opacity = page.evaluate(f"() => window.getComputedStyle(document.getElementById('{pg_id}')).opacity")
            children = page.evaluate(f"() => document.getElementById('{pg_id}').children.length")
            
            print(f"Tab: {tab.upper()}")
            print(f"  Page ID: {pg_id}")
            print(f"  Visible in CSS: {is_visible}")
            print(f"  Offset Height: {height}px")
            print(f"  Computed Opacity: {opacity}")
            print(f"  Children count: {children}")
            print("-" * 30)

        browser.close()

if __name__ == "__main__":
    run()
