from flask import Flask, render_template_string, request, Response
import requests
import json
import math
import csv
import io

# Загрузка регионов и отраслей из файлов
with open('areas.json', encoding='utf-8') as f:
    AREAS = json.load(f)
with open('industries.json', encoding='utf-8') as f:
    INDUSTRIES = json.load(f)

def get_area_options():
    options = []
    russia = next((c for c in AREAS if c['id'] == '113'), None)
    if russia:
        options.append({'id': russia['id'], 'name': russia['name']})
        for region in russia.get('areas', []):
            options.append({'id': region['id'], 'name': region['name']})
    return options

def get_industry_options():
    options = []
    for ind in INDUSTRIES:
        options.append({'id': ind['id'], 'name': ind['name']})
        for sub in ind.get('industries', []):
            options.append({'id': sub['id'], 'name': f"{sub['name']} ({ind['name']})"})
    return options

AREA_OPTIONS = get_area_options()
INDUSTRY_OPTIONS = get_industry_options()

app = Flask(__name__)

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <title>Поиск компаний на hh.ru</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {
            font-family: 'Segoe UI', 'Arial', sans-serif;
            background: #23272b;
            margin: 0;
            padding: 0;
            color: #f5f6fa;
        }
        .container {
            max-width: 900px;
            margin: 40px auto;
            background: #262a2e;
            border-radius: 14px;
            box-shadow: 0 2px 12px rgba(33,150,243,0.07);
            padding: 36px 28px 28px 28px;
            border: 1.5px solid #2a7a2a22;
        }
        h1 {
            text-align: center;
            color: #2196f3;
            margin-bottom: 32px;
            letter-spacing: 1px;
            font-weight: 600;
        }
        form {
            display: flex;
            flex-wrap: wrap;
            gap: 24px;
            align-items: flex-end;
            margin-bottom: 32px;
            background: #23272b;
            border-radius: 10px;
            padding: 24px 16px 8px 16px;
            box-shadow: 0 1px 4px rgba(33,150,243,0.04);
            border: 1px solid #2a7a2a22;
        }
        label {
            flex: 1 1 250px;
            display: flex;
            flex-direction: column;
            font-weight: 500;
            color: #bfc9d1;
        }
        select, input[type=text] {
            margin-top: 8px;
            padding: 10px 12px;
            border: 1px solid #3a4047;
            border-radius: 8px;
            font-size: 16px;
            background: #23272b;
            color: #f5f6fa;
            transition: border 0.2s;
        }
        select:focus, input[type=text]:focus {
            border: 1.5px solid #2196f3;
            outline: none;
        }
        button[type=submit], .download-btn {
            background: #2196f3;
            color: #fff;
            border: none;
            border-radius: 8px;
            padding: 12px 32px;
            font-size: 18px;
            font-weight: 600;
            cursor: pointer;
            box-shadow: 0 1px 4px rgba(33,150,243,0.10);
            transition: background 0.2s, box-shadow 0.2s;
        }
        button[type=submit]:hover, .download-btn:hover {
            background: #1976d2;
            box-shadow: 0 2px 8px rgba(33,150,243,0.13);
        }
        .company {
            background: #23272b;
            border-radius: 10px;
            box-shadow: 0 1.5px 8px rgba(33,150,243,0.07);
            padding: 24px 24px 18px 24px;
            margin-bottom: 22px;
            display: flex;
            gap: 20px;
            align-items: flex-start;
            border-left: 4px solid #2196f3;
            position: relative;
            cursor: pointer;
            transition: transform 0.13s cubic-bezier(.4,1.3,.6,1), box-shadow 0.13s, background 0.13s;
            border: 1px solid #2a7a2a22;
        }
        .company:hover {
            transform: scale(1.012) translateY(-1px);
            box-shadow: 0 4px 18px 0 #2196f355, 0 2px 8px rgba(33,150,243,0.10);
            background: #262a2e;
        }
        .avatar, .favicon {
            width: 54px;
            height: 54px;
            border-radius: 10px;
            background: #232c3b;
            color: #fff;
            font-size: 2.1rem;
            font-weight: bold;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 1px 4px rgba(33,150,243,0.10);
            flex-shrink: 0;
            letter-spacing: 1px;
            overflow: hidden;
        }
        .favicon img {
            width: 100%;
            height: 100%;
            object-fit: contain;
            border-radius: 10px;
            background: #fff;
        }
        .company-info {
            flex: 1 1 auto;
            min-width: 0;
        }
        .company-title {
            font-size: 1.18rem;
            font-weight: 600;
            color: #fff;
            margin-bottom: 4px;
            text-overflow: ellipsis;
            overflow: hidden;
            white-space: nowrap;
        }
        .company-link {
            color: #2196f3;
            text-decoration: none;
            font-size: 1.01rem;
            font-weight: 500;
        }
        .company-link:hover {
            text-decoration: underline;
        }
        .company-details {
            margin: 10px 0 0 0;
            font-size: 1.01rem;
            color: #bfc9d1;
            line-height: 1.7;
        }
        .company-details strong {
            color: #fff;
        }
        .count-badge {
            position: absolute;
            top: 16px;
            right: 20px;
            background: #2196f3;
            color: #fff;
            font-size: 1.13rem;
            font-weight: 700;
            border-radius: 8px;
            padding: 8px 18px 8px 14px;
            box-shadow: 0 1px 4px #2196f355;
            display: flex;
            align-items: center;
            gap: 7px;
            z-index: 2;
            letter-spacing: 1px;
        }
        .count-badge svg {
            width: 18px;
            height: 18px;
            fill: #fff;
        }
        .desc-block {
            border: 1.5px solid #2196f3;
            border-radius: 8px;
            background: #232c3b;
            color: #e3f2fd;
            padding: 10px 14px;
            margin: 12px 0 0 0;
            font-size: 1.01rem;
            line-height: 1.7;
            font-weight: 400;
            box-shadow: 0 1px 4px #2196f355;
        }
        .warn {
            color: #ff5252;
            font-weight: bold;
        }
        .pagination {
            margin: 32px 0 0 0;
            text-align: center;
            white-space: nowrap;
            overflow-x: auto;
        }
        .pagination a, .pagination span {
            margin: 0 6px;
            text-decoration: none;
            font-size: 18px;
            padding: 7px 16px;
            border-radius: 8px;
            color: #2196f3;
            background: #23272b;
            border: 1.5px solid #2196f3;
            transition: background 0.2s, color 0.2s, border 0.2s;
            display: inline-block;
        }
        .pagination .current {
            font-weight: bold;
            color: #fff;
            background: #2196f3;
            border: 1.5px solid #1976d2;
        }
        .pagination a:hover {
            background: #1976d2;
            color: #fff;
        }
        .download-section {
            margin-top: 20px;
            text-align: center;
        }
        @media (max-width: 600px) {
            .container { padding: 10px 2px; }
            form { flex-direction: column; gap: 12px; padding: 12px 4px 4px 4px; }
            label { font-size: 15px; }
            button[type=submit], .download-btn { width: 100%; }
            .company { flex-direction: column; gap: 10px; }
            .avatar, .favicon { margin-bottom: 8px; }
            .count-badge { position: static; margin-bottom: 10px; }
        }
        .timezone-info {
            margin-top: 10px;
            font-size: 15px;
            color: #90caf9;
            background: #23272b;
            border-radius: 8px;
            padding: 10px 14px;
            display: inline-block;
            border: 1.5px solid #2196f3;
        }
        .region-diff {
            color: #90caf9;
            font-size: 1.01rem;
            margin-top: 2px;
            margin-bottom: 8px;
        }
    </style>
    <script>
    const REGION_TIMEZONES = {
        '40': {zone: 1, desc: 'МСК-1 (UTC+2)', info: 'Калининградская область', diff: -1},
        '1': {zone: 2, desc: 'МСК (UTC+3)', info: 'г. Москва', diff: 0},
        '2': {zone: 2, desc: 'МСК (UTC+3)', info: 'г. Санкт-Петербург', diff: 0},
    };
    function getRegionDiff(areaName) {
        for (const key in REGION_TIMEZONES) {
            if (REGION_TIMEZONES[key].info === areaName || areaName.includes(REGION_TIMEZONES[key].info)) {
                const diff = REGION_TIMEZONES[key].diff;
                return (diff > 0 ? '+' : (diff < 0 ? diff : '')) + (diff !== 0 ? diff : '0');
            }
        }
        return null;
    }
    function showTimezoneInfo() {
        var select = document.getElementsByName('area')[0];
        var tzDiv = document.getElementById('tz-info');
        if (!select || !tzDiv) return;
        var val = select.value;
        if (REGION_TIMEZONES[val]) {
            var z = REGION_TIMEZONES[val];
            let diffStr = (z.diff > 0 ? '+' : (z.diff < 0 ? z.diff : '')) + (z.diff !== 0 ? z.diff : '0');
            tzDiv.innerHTML = `<b>Часовая зона:</b> ${z.zone} (${z.desc})<br><span>${z.info}</span><br><b>Разница с Москвой:</b> ${diffStr} ч.`;
            tzDiv.style.display = 'block';
        } else {
            tzDiv.innerHTML = '';
            tzDiv.style.display = 'none';
        }
    }
    window.addEventListener('DOMContentLoaded', function() {
        var select = document.getElementsByName('area')[0];
        if (select) {
            select.addEventListener('change', showTimezoneInfo);
            showTimezoneInfo();
        }
        document.querySelectorAll('.company').forEach(function(card) {
            card.addEventListener('click', function(e) {
                if (e.target.tagName === 'A') return;
                var link = card.querySelector('.company-link');
                if (link) {
                    window.open(link.href, '_blank');
                }
            });
        });
    });
    function goToPage(page) {
        var form = document.getElementById('search-form');
        if (form) {
            form.page.value = page;
            form.submit();
        }
    }
    </script>
</head>
<body>
    <div class="container">
    <h1>Поиск компаний на hh.ru</h1>
    <form method="post" id="search-form">
        <input type="hidden" name="page" value="{{ page }}">
        <label>Реги

он:
            <select name="area">
                <option value="">Любой</option>
                {% for area in area_options %}
                    <option value="{{ area.id }}" {% if params.area==area.id %}selected{% endif %}>{{ area.name }}</option>
                {% endfor %}
            </select>
            <span style="font-size: 12px; color: #888;">или введите ID: <input type="text" name="area_manual" value="{{ params.area_manual|default('') }}" style="width:60px"></span>
        </label>
        <button type="submit">Поиск</button>
    </form>
    <div id="tz-info" class="timezone-info" style="display:none;"></div>
    {% if companies is not none %}
        {% if companies|length > 0 %}
            <h2 style="color:#90caf9;">Компании, найдено всего: <strong>{{ total }}</strong></h2>
            <p style="color:#bfc9d1;">Показано компаний: <strong>{{ companies|length }}</strong>{% if total > 2000 %} <span class="warn">(отображается только часть из-за ограничений API hh.ru)</span>{% endif %}</p>
            {% for company in companies %}
                <div class="company" tabindex="0">
                    {% if company.site_url %}
                        <div class="favicon"><img src="https://www.google.com/s2/favicons?sz=64&domain_url={{ company.site_url }}" alt="favicon"></div>
                    {% else %}
                        <div class="avatar">{{ company.name[0]|upper }}</div>
                    {% endif %}
                    <div class="count-badge" title="Активных вакансий">
                        <svg viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59- their data as a CSV file
8Jon: 8 8-8 8s3.59 8 8 8-3.59 8-8 8zm-1-13h2v6h-2zm0 8h2v2h-2z"/></svg>
                        {{ company.open_vacancies }}
                    </div>
                    <div class="company-info">
                        <div class="company-title">{{ company.name }}</div>
                        <a class="company-link" href="{{ company.url }}" target="_blank">Профиль на hh.ru</a>
                        {% if company.area %}
                        <div class="region-diff">
                            <strong>Регион:</strong> {{ company.area }}
                            {% set diff = None %}
                            {% for key, val in REGION_TIMEZONES.items() %}
                                {% if val.info == company.area or company.area in val.info %}
                                    {% set diff = val.diff %}
                                {% endif %}
                            {% endfor %}
                            {% if diff is not none %}
                                 | <span>Разница с Москвой: <b>{{ "+" if diff > 0 else (diff if diff < 0 else "") }}{{ diff if diff != 0 else "0" }} ч.</b></span>
                            {% endif %}
                        </div>
                        {% endif %}
                        <div class="company-details">
                            {% if company.site_url %}<strong>Сайт:</strong> <a href="{{ company.site_url }}" style="color:#2196f3;" target="_blank">{{ company.site_url }}</a><br>{% endif %}
                            {% if company.type %}<strong>Тип:</strong> {{ company.type }}<br>{% endif %}
                            {% if company.founded %}<strong>Год основания:</strong> {{ company.founded }}<br>{% endif %}
                            {% if company.vacancies_url %}<strong>Вакансии:</strong> <a href="{{ company.vacancies_url }}" class="company-link" target="_blank">Смотреть</a><br>{% endif %}
                        </div>
                        {% if company.description %}
                        <div class="desc-block">
                            {% set desc = company.description|safe %}
                            {% set paragraphs = desc.split('</p>') if '</p>' in desc else desc.split('\n\n') %}
                            {% for p in paragraphs[:2] %}{{ p|safe }}{% if '</p>' in desc %}</p>{% else %}<br><br>{% endif %}{% endfor %}
                        </div>
                        {% endif %}
                    </div>
                </div>
            {% endfor %}
            <div class="download-section">
                <form method="post" action="/download">
                    <input type="hidden" name="keyword" value="{{ params.keyword }}">
                    <input type="hidden" name="area" value="{{ params.area }}">
                    <input type="hidden" name="area_manual" value="{{ params.area_manual }}">
                    <input type="hidden" name="industry" value="{{ params.industry }}">
                    <input type="hidden" name="industry_manual" value="{{ params.industry_manual }}">
                    <input type="hidden" name="page" value="{{ page }}">
                    <button type="submit" class="download-btn">Скачать в CSV</button>
                </form>
            </div>
        {% endif %}
        {% if total_pages > 1 %}
        <div class="pagination">
            {% if page > 1 %}
                <a href="#" onclick="goToPage({{ page-1 }}); return false;">« Назад</a>
            {% endif %}
            {% for p in range(1, total_pages+1) %}
                {% if p == page %}
                    <span class="current">{{ p }}</span>
                {% elif p <= 2 or p > total_pages-2 or (p >= page-2 and p <= page+2) %}
                    <a href="#" onclick="goToPage({{ p }}); return false;">{{ p }}</a>
                {% elif p == 3 and page > 5 %}
                    ...
                {% elif p == total_pages-2 and page < total_pages-4 %}
                    ...
                {% endif %}
            {% endfor %}
            {% if page < total_pages %}
                <a href="#" onclick="goToPage({{ page+1 }}); return false;">Вперёд »</a>
            {% endif %}
        </div>
        {% endif %}
    {% endif %}
    </div>
</body>
</html>
'''

def search_companies(params, per_page=100, max_api_pages=20):
    url = "https://api.hh.ru/employers"
    headers = {"User-Agent": "api-test-agent"}
    page = params.get('page', 1)
    result = []
    total_found = 0
    api_page = 0
    shown = 0
    skip = (page - 1) * per_page
    filtered_count = 0
    industry_val = params.get("industry_manual").strip() if params.get("industry_manual") else params.get("industry")
    while api_page < max_api_pages and len(result) < per_page:
        query = {"per_page": 100, "page": api_page, "only_with_vacancies": True, "sort_by": "by_vacancies_open"}
        area_val = params.get("area_manual") or params.get("area")
        if area_val: query["area"] = area_val
        if industry_val: query["industry"] = industry_val
        try:
            response = requests.get(url, headers=headers, params=query)
            response.raise_for_status()
            data = response.json()
            if api_page == 0:
                total_found = data.get("found", 0)
            employers = data.get("items", [])
            for emp in employers:
                if industry_val:
                    inds = emp.get("industries", [])
                    if not any(ind.get("id") == industry_val for ind in inds):
                        continue
                if filtered_count < skip:
                    filtered_count += 1
                    continue
                if len(result) < per_page:
                    emp_details = emp.copy()
                    try:
                        details_resp = requests.get(f"https://api.hh.ru/employers/{emp['id']}", headers=headers)
                        if details_resp.status_code == 200:
                            details = details_resp.json()
                            emp_details.update(details)
                    except Exception:
                        pass
                    area_val = emp_details.get("area")
                    if isinstance(area_val, dict):
                        area_name = area_val.get("name", "")
                    else:
                        area_name = str(area_val) if area_val else ""
                    type_val = emp_details.get("type")
                    if isinstance(type_val, dict):
                        type_name = type_val.get("name", "")
                    else:
                        type_name = str(type_val) if type_val else ""
                    result.append({
                        "name": emp_details.get("name", ""),
                        "open_vacancies": emp_details.get("open_vacancies", 0),
                        "url": emp_details.get("alternate_url", ""),
                        "area": area_name,
                        "site_url": emp_details.get("site_url", ""),
                        "type": type_name,
                        "founded": emp_details.get("founded", ""),
                        "description": emp_details.get("description", ""),
                        "vacancies_url": emp_details.get("vacancies_url", "")
                    })
            if not employers:
                break
        except requests.exceptions.RequestException as e:
            print(f"Ошибка при получении компаний: {e}")
            break
        api_page += 1
    return result, total_found

@app.route('/', methods=['GET', 'POST'])
def index():
    companies = None
    total = 0
    params = {
        "keyword": '', "area": '', "area_manual": '', "industry": '', "industry_manual": '', "page": 1
    }
    page = 1
    per_page = 100
    total_pages = 1
    REGION_TIMEZONES = {
        '40': {'zone': 1, 'desc': 'МСК-1 (UTC+2)', 'info': 'Калининградская область', 'diff': -1},
        '1': {'zone': 2, 'desc': 'МСК (UTC+3)', 'info': 'г. Москва', 'diff': 0},
        '2': {'zone': 2, 'desc': 'МСК (UTC+3)', 'info': 'г. Санкт-Петербург', 'diff': 0},
    }
    if request.method == 'POST':
        params["keyword"] = request.form.get('keyword', '').strip()
        params["area"] = request.form.get('area', '').strip()
        params["area_manual"] = request.form.get('area_manual', '').strip()
        params["industry"] = request.form.get('industry', '').strip()
        params["industry_manual"] = request.form.get('industry_manual', '').strip()
        try:
            page = int(request.form.get('page', '1'))
        except Exception:
            page = 1
        params["page"] = page
        companies, total = search_companies(params, per_page=per_page)
        total_pages = math.ceil(total / per_page) if total else 1
    return render_template_string(HTML_TEMPLATE, companies=companies, total=total, params=params, area_options=AREA_OPTIONS, industry_options=INDUSTRY_OPTIONS, page=page, total_pages=total_pages, REGION_TIMEZONES=REGION_TIMEZONES)

@app.route('/download', methods=['POST'])
def download_csv():
    params = {
        "keyword": request.form.get('keyword', '').strip(),
        "area": request.form.get('area', '').strip(),
        "area_manual": request.form.get('area_manual', '').strip(),
        "industry": request.form.get('industry', '').strip(),
        "industry_manual": request.form.get('industry_manual', '').strip(),
        "page": int(request.form.get('page', '1'))
    }
    companies, _ = search_companies(params, per_page=100)
    
    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)
    
    # Write headers
    headers = ["name", "open_vacancies", "url", "area", "site_url", "type", "founded", "vacancies_url"]
    writer.writerow(headers)
    
    # Write company data (excluding description)
    for company in companies:
        row = [
            company.get("name", ""),
            company.get("open_vacancies", 0),
            company.get("url", ""),
            company.get("area", ""),
            company.get("site_url", ""),
            company.get("type", ""),
            company.get("founded", ""),
            company.get("vacancies_url", "")
        ]
        writer.writerow(row)
    
    # Prepare response
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={
            'Content-Disposition': 'attachment; filename=companies.csv',
            'Content-Type': 'text/csv; charset=utf-8'
        }
    )

if __name__ == "__main__":
    app.run(debug=True)