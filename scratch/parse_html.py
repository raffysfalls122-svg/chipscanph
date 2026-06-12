from html.parser import HTMLParser

class DivTracker(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack = []
        self.results = {}

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        el_id = attrs_dict.get('id')
        el_class = attrs_dict.get('class')
        
        if tag == 'div':
            self.stack.append((el_id, el_class))
            if el_id in ['pg-scan', 'pg-grades', 'pg-prices', 'pg-ref', 'pg-manual', 'pg-history', 'pg-admin']:
                # Parent is the second to last item on the stack if it exists
                parent = self.stack[-2] if len(self.stack) > 1 else None
                self.results[el_id] = parent

    def handle_endtag(self, tag):
        if tag == 'div':
            if self.stack:
                self.stack.pop()

with open("scanner/templates/scanner/index.html", "r", encoding="utf-8") as f:
    html = f.read()

tracker = DivTracker()
tracker.feed(html)

print("--- Div parents according to HTMLParser ---")
for el_id, parent in tracker.results.items():
    print(f"Element #{el_id} parent is: {parent}")
