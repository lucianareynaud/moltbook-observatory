#!/bin/sh
# Build static site index from all generated weekly reports

set -e

VENV=".venv"
BIN="$VENV/bin"
OUTPUT_DIR="output"
SITE_DIR="$OUTPUT_DIR/site"

if [ ! -d "$VENV" ]; then
    echo "[build-site] ERROR: Virtual environment not found. Run 'make setup' first."
    exit 1
fi

echo "[build-site] Building static site index..."

# Create site directory
mkdir -p "$SITE_DIR"

# Generate index.html that lists all weekly reports
"$BIN/python" -c "
import os
from pathlib import Path
from datetime import datetime

output_dir = Path('$OUTPUT_DIR')
site_dir = Path('$SITE_DIR')

# Find all weekly report directories
week_dirs = sorted([d for d in output_dir.iterdir() if d.is_dir() and d.name.startswith('20')], reverse=True)

if not week_dirs:
    print('[build-site] No weekly reports found. Run make report first.')
    exit(1)

# Generate index.html
html = '''<!DOCTYPE html>
<html lang=\"en\">
<head>
    <meta charset=\"UTF-8\">
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
    <title>Moltbook Observatory — Reports</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, \"Segoe UI\", Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f5f5f5;
            padding: 20px;
        }
        .container {
            max-width: 900px;
            margin: 0 auto;
            background: white;
            padding: 40px;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        h1 {
            color: #1e40af;
            border-bottom: 3px solid #2563eb;
            padding-bottom: 15px;
            margin-bottom: 30px;
        }
        .meta {
            color: #6b7280;
            font-size: 0.9rem;
            margin-bottom: 30px;
        }
        .reports-list {
            list-style: none;
        }
        .report-item {
            border: 1px solid #e5e7eb;
            border-radius: 6px;
            padding: 20px;
            margin-bottom: 15px;
            transition: all 0.2s;
        }
        .report-item:hover {
            border-color: #2563eb;
            box-shadow: 0 2px 8px rgba(37,99,235,0.1);
        }
        .report-item h2 {
            color: #1e40af;
            font-size: 1.3rem;
            margin-bottom: 10px;
        }
        .report-links {
            display: flex;
            gap: 15px;
            margin-top: 12px;
        }
        .report-links a {
            color: #2563eb;
            text-decoration: none;
            font-weight: 500;
            padding: 6px 12px;
            border: 1px solid #2563eb;
            border-radius: 4px;
            transition: all 0.2s;
        }
        .report-links a:hover {
            background: #2563eb;
            color: white;
        }
        footer {
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #e5e7eb;
            color: #6b7280;
            font-size: 0.85rem;
            text-align: center;
        }
    </style>
</head>
<body>
    <div class=\"container\">
        <h1>Moltbook Observatory — Weekly Reports</h1>
        <div class=\"meta\">
            <strong>Generated:</strong> ''' + datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC') + '''<br>
            <strong>Total Reports:</strong> ''' + str(len(week_dirs)) + '''
        </div>
        <ul class=\"reports-list\">
'''

for week_dir in week_dirs:
    week_id = week_dir.name
    report_exists = (week_dir / 'report.md').exists()
    dashboard_exists = (week_dir / 'dashboard.html').exists()

    if report_exists or dashboard_exists:
        html += f'''
            <li class=\"report-item\">
                <h2>{week_id}</h2>
                <div class=\"report-links\">
'''
        if dashboard_exists:
            html += f'                    <a href=\"../{week_id}/dashboard.html\">📊 Dashboard</a>\n'
        if report_exists:
            html += f'                    <a href=\"../{week_id}/report.md\">📄 Markdown Report</a>\n'

        html += '''                </div>
            </li>
'''

html += '''        </ul>
        <footer>
            <p><strong>Moltbook Observatory</strong> — Public-only integrity monitoring</p>
            <p>All reports are deterministic transforms of collected raw data.</p>
        </footer>
    </div>
</body>
</html>
'''

# Write index.html
index_path = site_dir / 'index.html'
index_path.write_text(html, encoding='utf-8')

print(f'[build-site] ✓ Generated site index: {index_path}')
print(f'[build-site] Found {len(week_dirs)} weekly report(s)')
print(f'[build-site] Open file://{index_path.absolute()} in your browser')
"

echo "[build-site] ✓ Site built successfully"
