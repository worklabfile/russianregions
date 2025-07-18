from flask import Flask, render_template_string, request
import requests
import json

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
    </style>
</head>
<body>
    <h1>Поиск компаний на hh.ru</h1>
    <form method="post">
        <input type="text" name="keyword" placeholder="Ключевое слово (например, Python)" value="{{ keyword|default('') }}">
        <input type="text" name="area" placeholder="ID региона (например, 1 — Москва)" value="{{ area|default('') }}">
        <button type="submit">Поиск</button>
    </form>
    {% if companies is not none %}
        <h2>Компании с более чем 5 активными вакансиями:</h2>
        <p>Всего найдено компаний: <strong>{{ total }}</strong></p>
        {% if companies %}
            {% for company in companies %}
                <div class="company">
                    <strong>Компания:</strong> <a href="{{ company.url }}" target="_blank">{{ company.name }}</a><br>
                    <strong>Активных вакансий:</strong> <span class="count">{{ company.open_vacancies }}</span><br>
                </div>
            {% endfor %}
        {% else %}
            <p>Компаний с более чем 5 активными вакансиями не найдено.</p>
        {% endif %}
    {% endif %}
</body>
</html>
'''

def search_companies(keyword='', area=None, min_vacancies=5, per_page=100, max_pages=20):
    url = "https://api.hh.ru/employers"
    headers = {"User-Agent": "api-test-agent"}
    result = []
    for page in range(max_pages):
        params = {
            "text": keyword,
            "per_page": per_page,
            "page": page,
            "only_with_vacancies": True
        }
        if area:
            params["area"] = area
        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            employers = data.get("items", [])
            for emp in employers:
                open_vacancies = emp.get("open_vacancies", 0)
                if open_vacancies > min_vacancies:
                    result.append({
                        "name": emp.get("name", ""),
                        "open_vacancies": open_vacancies,
                        "url": emp.get("alternate_url", "")
                    })
            if not employers:
                break
        except requests.exceptions.RequestException as e:
            print(f"Ошибка при получении компаний: {e}")
            break
    return result

@app.route('/', methods=['GET', 'POST'])
def index():
    companies = None
    keyword = ''
    area = ''
    total = 0
    if request.method == 'POST':
        keyword = request.form.get('keyword', '').strip()
        area = request.form.get('area', '').strip()
        companies = search_companies(keyword=keyword, area=area if area else None)
        total = len(companies) if companies else 0
    return render_template_string(HTML_TEMPLATE, companies=companies, keyword=keyword, area=area, total=total)

if __name__ == "__main__":
    app.run(debug=True)