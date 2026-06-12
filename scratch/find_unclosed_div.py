from html.parser import HTMLParser

class ScanDivFinder(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_scan = False
        self.div_stack = []
        self.line_num = 1

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        el_id = attrs_dict.get('id')
        el_class = attrs_dict.get('class')
        
        if tag == 'div' and el_id == 'pg-scan':
            self.in_scan = True
            
        if self.in_scan:
            if tag == 'div':
                self.div_stack.append((el_id, el_class, self.line_num))
                print(f"[{self.line_num}] Open DIV: id={el_id}, class={el_class}. Stack depth={len(self.div_stack)}")

    def handle_endtag(self, tag):
        if self.in_scan:
            if tag == 'div':
                if self.div_stack:
                    el_id, el_class, start_line = self.div_stack.pop()
                    print(f"[{self.line_num}] Close DIV: opened on line {start_line} (id={el_id}, class={el_class}). Stack depth={len(self.div_stack)}")
                    if not self.div_stack:
                        print(f"[{self.line_num}] End of #pg-scan!")
                        self.in_scan = False
                else:
                    print(f"[{self.line_num}] Unexpected Close DIV (empty stack)!")

with open("scanner/templates/scanner/index.html", "r", encoding="utf-8") as f:
    lines = f.readlines()

finder = ScanDivFinder()
# Run only up to line 3470
for idx in range(min(3470, len(lines))):
    finder.line_num = idx + 1
    finder.feed(lines[idx])
