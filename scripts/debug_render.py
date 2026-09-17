import html
import json
import os
import time
from selenium import webdriver
from selenium.webdriver.edge.options import Options
import sys
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.abspath("."))
import generate_architecture_drawio as g

xml_data = g.build_xml()
config = {
    'highlight': '#0000ff',
    'nav': False,
    'resize': False,
    'toolbar': None,
    'edit': None,
    'xml': xml_data,
    'check-visible-state': False
}
escaped_config = html.escape(json.dumps(config))
html_content = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <script src="https://viewer.diagrams.net/js/viewer-static.min.js"></script>
</head>
<body>
  <div class="mxgraph" style="max-width:100%;border:none;" data-mxgraph="{escaped_config}"></div>
</body>
</html>
"""
with open("debug_render.html", "w", encoding="utf-8") as f:
    f.write(html_content)

options = Options()
options.add_argument("--headless=new")
options.add_argument("--window-size=2400,1350")
options.set_capability("goog:loggingPrefs", {"browser": "ALL"})

driver = webdriver.Edge(options=options)
try:
    temp_html = os.path.abspath("debug_render.html")
    driver.get(f"file:///{temp_html}")
    time.sleep(2)
    print("Trying GraphViewer.processElements()...")
    res = driver.execute_script('''
        try {
            if (window.GraphViewer && window.GraphViewer.processElements) {
                window.GraphViewer.processElements();
                return "called processElements";
            }
            return "GraphViewer not found";
        } catch(e) {
            return "Error: " + e.message + " stack: " + e.stack;
        }
    ''')
    print("processElements result:", res)
    time.sleep(3)
    print("Has svg now?", "<svg" in driver.page_source)
    for entry in driver.get_log("browser"):
        print("BROWSER LOG:", entry)
finally:
    driver.quit()
