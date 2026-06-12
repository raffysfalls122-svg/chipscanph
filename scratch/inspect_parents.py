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

        # Trace parents
        trace = page.evaluate("""() => {
            const el = document.getElementById('pg-grades');
            const path = [];
            let current = el;
            while (current) {
                const style = window.getComputedStyle(current);
                path.push({
                    tag: current.tagName,
                    id: current.id,
                    className: current.className,
                    display: style.display,
                    height: style.height,
                    offsetHeight: current.offsetHeight,
                    opacity: style.opacity,
                    visibility: style.visibility
                });
                current = current.parentElement;
            }
            return path;
        }""")

        with open("scratch/inspect_parents.txt", "w", encoding="utf-8") as f:
            f.write("--- Ancestor Path for pg-grades ---\n")
            for idx, item in enumerate(trace):
                f.write(f"Level {idx}: {item}\n")

        print("Done. Trace written to scratch/inspect_parents.txt")
        browser.close()

if __name__ == "__main__":
    run()
