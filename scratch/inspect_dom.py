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

        # Click GRADES
        page.click("#nb-grades")
        time.sleep(0.5)

        outer_html = page.evaluate("() => document.getElementById('pg-grades').outerHTML")
        children_info = page.evaluate("""() => {
            const children = Array.from(document.getElementById('pg-grades').children);
            return children.map(c => ({
                tag: c.tagName,
                id: c.id,
                className: c.className,
                offsetHeight: c.offsetHeight,
                display: window.getComputedStyle(c).display
            }));
        }""")

        with open("scratch/inspect_dom_output.txt", "w", encoding="utf-8") as f:
            f.write("--- pg-grades Outer HTML ---\n")
            f.write(outer_html + "\n\n")
            f.write("--- Children of pg-grades and their heights ---\n")
            for idx, info in enumerate(children_info):
                f.write(f"Child {idx}: {info}\n")

        print("Done. Output written to scratch/inspect_dom_output.txt")
        browser.close()

if __name__ == "__main__":
    run()
