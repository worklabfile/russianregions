from flask import Flask, render_template_string, request
import requests
import json

app = Flask(__name__)

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <title>Поиск вакансий на hh.ru</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        form { margin-bottom: 30px; }
        .vacancy { border-bottom: 1px solid #ccc; padding: 10px 0; }
        .vacancy:last-child { border-bottom: none; }
        .salary { color: #2a7a2a; }
    </style>
</head>
<body>
    <h1>Поиск вакансий на hh.ru</h1>
    <form method="post">
        <input type="text" name="keyword" placeholder="Ключевое слово (например, Python разработчик)" value="{{ keyword|default('') }}" required>
        <button type="submit">Поиск</button>
    </form>
    {% if vacancies is not none %}
        {% if vacancies %}
            <h2>Найдено {{ vacancies|length }} вакансий по запросу '{{ keyword }}':</h2>
            {% for vacancy in vacancies %}
                <div class="vacancy">
                    <strong>Название:</strong> {{ vacancy.title }}<br>
                    <strong>Компания:</strong> {{ vacancy.company }}<br>
                    <strong>Город:</strong> {{ vacancy.city }}<br>
                    <strong>Зарплата:</strong> <span class="salary">{{ vacancy.salary_str }}</span><br>
                    <strong>Телефон:</strong> {{ vacancy.phone or 'Не указан' }}<br>
                    <a href="{{ vacancy.url }}" target="_blank">Ссылка</a>
                </div>
            {% endfor %}
        {% else %}
            <p>Вакансий по запросу '{{ keyword }}' не найдено.</p>
        {% endif %}
    {% endif %}
</body>
</html>
'''

def get_vacancy_phone(vacancy_id):
    url = f"https://api.hh.ru/vacancies/{vacancy_id}"
    headers = {"User-Agent": "api-test-agent"}
    try:
        resp = requests.get(url, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        contacts = data.get("contacts")
        if contacts and "phones" in contacts and contacts["phones"]:
            phone = contacts["phones"][0]
            phone_str = phone.get("formatted", "")
            if not phone_str:
                # Формируем вручную, если нет formatted
                country = phone.get("country", "")
                city = phone.get("city", "")
                number = phone.get("number", "")
                ext = phone.get("ext")
                phone_str = f"+{country} ({city}) {number}"
                if ext:
                    phone_str += f" доб. {ext}"
            return phone_str
    except Exception:
        pass
    return None

def search_vacancies(keyword, area=1, per_page=100):
    url = "https://api.hh.ru/vacancies"
    headers = {"User-Agent": "api-test-agent"}
    params = {
        "text": keyword,
        "area": area,
        "per_page": per_page
    }
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        vacancies = data.get("items", [])
        result = []
        for vacancy in vacancies:
            salary = vacancy.get("salary", None)
            salary_str = "Не указана"
            if salary:
                salary_from = salary.get("from")
                salary_to = salary.get("to")
                currency = salary.get("currency")
                salary_parts = []
                if salary_from:
                    salary_parts.append(f"от {salary_from}")
                if salary_to:
                    salary_parts.append(f"до {salary_to}")
                if currency:
                    salary_parts.append(currency)
                salary_str = " ".join(str(part) for part in salary_parts)
            phone = get_vacancy_phone(vacancy.get("id"))
            vacancy_info = {
                "title": vacancy.get("name", ""),
                "company": vacancy.get("employer", {}).get("name", ""),
                "city": vacancy.get("area", {}).get("name", ""),
                "salary": salary,
                "salary_str": salary_str,
                "url": vacancy.get("alternate_url", ""),
                "phone": phone
            }
            result.append(vacancy_info)
        return result
    except requests.exceptions.RequestException as e:
        print(f"Ошибка при получении вакансий: {e}")
        return []

@app.route('/', methods=['GET', 'POST'])
def index():
    vacancies = None
    keyword = ''
    if request.method == 'POST':
        keyword = request.form.get('keyword', '').strip()
        if keyword:
            vacancies = search_vacancies(keyword)
    return render_template_string(HTML_TEMPLATE, vacancies=vacancies, keyword=keyword)

if __name__ == "__main__":
    app.run(debug=True)