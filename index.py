from flask import Flask, render_template_string, request
import requests
import json
import math

# Загрузка регионов и отраслей из файлов
with open('areas.json', encoding='utf-8') as f:
    AREAS = json.load(f)
with open('industries.json', encoding='utf-8') as f:
    INDUSTRIES = json.load(f)

def get_area_options():
    # Только регионы России (id=113)
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
            background: #2c3136;
            border-radius: 18px;
            box-shadow: 0 4px 32px rgba(0,0,0,0.18);
            padding: 36px 28px 28px 28px;
        }
        h1 {
            text-align: center;
            color: #2196f3;
            margin-bottom: 32px;
            letter-spacing: 1px;
        }
        form {
            display: flex;
            flex-wrap: wrap;
            gap: 24px;
            align-items: flex-end;
            margin-bottom: 32px;
            background: #23272b;
            border-radius: 12px;
            padding: 24px 16px 8px 16px;
            box-shadow: 0 2px 8px rgba(33,150,243,0.08);
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
        button[type=submit] {
            background: linear-gradient(90deg, #2196f3 60%, #1976d2 100%);
            color: #fff;
            border: none;
            border-radius: 8px;
            padding: 12px 32px;
            font-size: 18px;
            font-weight: 600;
            cursor: pointer;
            box-shadow: 0 2px 8px rgba(33,150,243,0.12);
            transition: background 0.2s, box-shadow 0.2s;
        }
        button[type=submit]:hover {
            background: linear-gradient(90deg, #1976d2 60%, #2196f3 100%);
            box-shadow: 0 4px 16px rgba(33,150,243,0.18);
        }
        .company {
            background: #23272b;
            border-radius: 14px;
            box-shadow: 0 1px 8px rgba(33,150,243,0.08);
            padding: 22px 24px 18px 24px;
            margin-bottom: 22px;
            display: flex;
            gap: 20px;
            align-items: flex-start;
            border-left: 5px solid #2196f3;
        }
        .company:last-child {
            margin-bottom: 0;
        }
        .avatar {
            width: 54px;
            height: 54px;
            border-radius: 10px;
            background: #2196f3;
            color: #fff;
            font-size: 2.1rem;
            font-weight: bold;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 2px 8px rgba(33,150,243,0.18);
            flex-shrink: 0;
        }
        .company-info {
            flex: 1 1 auto;
        }
        .company-title {
            font-size: 1.25rem;
            font-weight: 600;
            color: #fff;
            margin-bottom: 4px;
        }
        .company-link {
            color: #90caf9;
            text-decoration: none;
            font-size: 1.05rem;
        }
        .company-link:hover {
            text-decoration: underline;
        }
        .company-details {
            margin: 8px 0 0 0;
            font-size: 1rem;
            color: #bfc9d1;
        }
        .company-details strong {
            color: #fff;
        }
        .count {
            color: #2196f3;
            font-weight: bold;
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
        @media (max-width: 600px) {
            .container { padding: 10px 2px; }
            form { flex-direction: column; gap: 12px; padding: 12px 4px 4px 4px; }
            label { font-size: 15px; }
            button[type=submit] { width: 100%; }
            .company { flex-direction: column; gap: 10px; }
            .avatar { margin-bottom: 8px; }
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
    </style>
    <script>
    // Карта регионов к часовым зонам (id региона -> инфо)
    const REGION_TIMEZONES = {
        '40': {zone: 1, desc: 'МСК-1 (UTC+2)', info: 'Калининградская область', diff: -1},
        '1': {zone: 2, desc: 'МСК (UTC+3)', info: 'г. Москва', diff: 0},
        '2': {zone: 2, desc: 'МСК (UTC+3)', info: 'г. Санкт-Петербург', diff: 0},
        // ... остальные регионы ...
    };
    function showTimezoneInfo() {
        var select = document.getElementsByName('area')[0];
        var tzDiv = document.getElementById('tz-info');
        if (!select || !tzDiv) return;
        var val = select.value;
        if (REGION_TIMEZONES[val]) {
            var z = REGION_TIMEZONES[val];
            let diffStr = (z.diff > 0 ? '+' : (z.diff < 0 ? z.diff : '')) + (z.diff !== 0 ? z.diff : '');
            tzDiv.innerHTML = `<b>Часовая зона:</b> ${z.zone} (${z.desc})<br><span>${z.info}</span><br><b>Разница с Москвой:</b> ${diffStr ? diffStr : '0'} ч.`;
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
        <label>Регион:
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
                <div class="company">
                    <div class="avatar">{{ company.name[0]|upper }}</div>
                    <div class="company-info">
                        <div class="company-title">{{ company.name }}</div>
                        <a class="company-link" href="{{ company.url }}" target="_blank">Профиль на hh.ru</a>
                        <div class="company-details">
                            <strong>Активных вакансий:</strong> <span class="count">{{ company.open_vacancies }}</span><br>
                            {% if company.area %}<strong>Регион:</strong> {{ company.area }}<br>{% endif %}
                            {% if company.site_url %}<strong>Сайт:</strong> <a href="{{ company.site_url }}" style="color:#90caf9;" target="_blank">{{ company.site_url }}</a><br>{% endif %}
                            {% if company.type %}<strong>Тип:</strong> {{ company.type }}<br>{% endif %}
                            {% if company.founded %}<strong>Год основания:</strong> {{ company.founded }}<br>{% endif %}
                            {% if company.description %}<strong>Описание:</strong> {{ company.description|safe }}<br>{% endif %}
                            {% if company.vacancies_url %}<strong>Вакансии:</strong> <a href="{{ company.vacancies_url }}" style="color:#90caf9;" target="_blank">Смотреть</a><br>{% endif %}
                        </div>
                    </div>
                </div>
            {% endfor %}
        {% endif %}
        {% if total_pages > 1 %}
        <div class="pagination">
            {% if page > 1 %}
                <a href="#" onclick="goToPage({{ page-1 }}); return false;">&laquo; Назад</a>
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
                <a href="#" onclick="goToPage({{ page+1 }}); return false;">Вперёд &raquo;</a>
            {% endif %}
        </div>
        {% endif %}
    {% endif %}
    </div>
</body>
</html>
'''

# В функции search_companies теперь нужно получать больше информации о компании

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
                    # Получаем подробную информацию о компании
                    emp_details = emp.copy()
                    try:
                        details_resp = requests.get(f"https://api.hh.ru/employers/{emp['id']}", headers=headers)
                        if details_resp.status_code == 200:
                            details = details_resp.json()
                            emp_details.update(details)
                    except Exception:
                        pass
                    # Безопасно извлекаем поля, которые могут быть строкой или словарём
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
    return render_template_string(HTML_TEMPLATE, companies=companies, total=total, params=params, area_options=AREA_OPTIONS, industry_options=INDUSTRY_OPTIONS, page=page, total_pages=total_pages)

if __name__ == "__main__":
    app.run(debug=True)