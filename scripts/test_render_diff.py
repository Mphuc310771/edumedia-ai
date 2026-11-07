import subprocess, os, html, json, time
from selenium import webdriver
from selenium.webdriver.edge.options import Options

from pathlib import Path
AGENT_SYS_DIR = Path(__file__).resolve().parents[1]
old_xml = subprocess.check_output(['git', 'show', 'HEAD:docs/agentsys-architecture.drawio'], cwd=str(AGENT_SYS_DIR)).decode('utf-8')
config = {
    'highlight': '#0000ff',
    'nav': False,
    'resize': False,
    'toolbar': None,
    'edit': None,
    'xml': old_xml,
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
with open('test_old.html', 'w', encoding='utf-8') as f:
    f.write(html_content)

options = Options()
options.add_argument('--headless=new')
options.add_argument('--window-size=2400,1350')
driver = webdriver.Edge(options=options)
try:
    driver.get('file:///' + os.path.abspath('test_old.html').replace('\\', '/'))
    time.sleep(4)
    svg_count = driver.execute_script('return document.querySelectorAll("svg").length;')
    print('Old XML SVG count:', svg_count)
finally:
    driver.quit()
