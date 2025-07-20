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
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        form { margin-bottom: 30px; }
        .company { border-bottom: 1px solid #ccc; padding: 10px 0; }
        .company:last-child { border-bottom: none; }
        .count { color: #2a7a2a; }
        label { display: block; margin-top: 10px; }
        select, input[type=text] { min-width: 200px; }
        .warn { color: #b00; font-weight: bold; }
        .pagination { margin: 20px 0; }
        .pagination a, .pagination span { margin: 0 5px; text-decoration: none; }
        .pagination .current { font-weight: bold; color: #333; }
    </style>
    <script>
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
    <h1>Поиск компаний на hh.ru</h1>
    <form method="post" id="search-form">
        <input type="hidden" name="page" value="{{ page }}">
        <label>Ключевое слово:
            <input type="text" name="keyword" placeholder="например, Python" value="{{ params.keyword|default('') }}">
        </label>
        <label>Регион:
            <select name="area">
                <option value="">Любой</option>
                {% for area in area_options %}
                    <option value="{{ area.id }}" {% if params.area==area.id %}selected{% endif %}>{{ area.name }}</option>
                {% endfor %}
            </select>
            <span style="font-size: 12px; color: #888;">или введите ID: <input type="text" name="area_manual" value="{{ params.area_manual|default('') }}" style="width:60px"></span>
        </label>
        <label>Отрасль:
            <select name="industry">
                <option value="">Любая</option>
                {% for ind in industry_options %}
                    <option value="{{ ind.id }}" {% if params.industry==ind.id %}selected{% endif %}>{{ ind.name }}</option>
                {% endfor %}
            </select>
            <span style="font-size: 12px; color: #888;">или введите ID: <input type="text" name="industry_manual" value="{{ params.industry_manual|default('') }}" style="width:60px"></span>
        </label>
        <button type="submit">Поиск</button>
    </form>
    {% if companies is not none %}
        {% if companies|length > 0 %}
            <h2>Компании, найдено всего: <strong>{{ total }}</strong></h2>
            <p>Показано компаний: <strong>{{ companies|length }}</strong>{% if total > 2000 %} <span class="warn">(отображается только часть из-за ограничений API hh.ru)</span>{% endif %}</p>
            {% for company in companies %}
                <div class="company">
                    <strong>Компания:</strong> <a href="{{ company.url }}" target="_blank">{{ company.name }}</a><br>
                    <strong>Активных вакансий:</strong> <span class="count">{{ company.open_vacancies }}</span><br>
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
</body>
</html>
'''

def search_companies(params, per_page=50, max_api_pages=10):
    url = "https://api.hh.ru/employers"
    headers = {"User-Agent": "api-test-agent"}
    page = params.get('page', 1)
    result = []
    total_found = 0
    api_page = 0
    shown = 0
    skip = (page - 1) * per_page
    filtered_count = 0
    # Определяем, какой industry использовать
    industry_val = params.get("industry_manual").strip() if params.get("industry_manual") else params.get("industry")
    while api_page < max_api_pages and len(result) < per_page:
        query = {"per_page": 50, "page": api_page, "only_with_vacancies": True}
        if params.get("keyword"): query["text"] = params["keyword"]
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
                # Строгая фильтрация по отрасли на клиенте
                if industry_val:
                    inds = emp.get("industries", [])
                    if not any(ind.get("id") == industry_val for ind in inds):
                        continue
                if filtered_count < skip:
                    filtered_count += 1
                    continue
                if len(result) < per_page:
                    result.append({
                        "name": emp.get("name", ""),
                        "open_vacancies": emp.get("open_vacancies", 0),
                        "url": emp.get("alternate_url", "")
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
    per_page = 50
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