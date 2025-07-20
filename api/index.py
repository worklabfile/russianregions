import json
import math
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import httpx
import os

app = FastAPI()
templates = Jinja2Templates(directory="templates")

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

AREA_OPTIONS = get_area_options()

# Карта регионов для шаблона (должна совпадать с JS)
REGION_TIMEZONES = {
    '40': {'zone': 1, 'desc': 'МСК-1 (UTC+2)', 'info': 'Калининградская область', 'diff': -1},
    '1': {'zone': 2, 'desc': 'МСК (UTC+3)', 'info': 'г. Москва', 'diff': 0},
    '2': {'zone': 2, 'desc': 'МСК (UTC+3)', 'info': 'г. Санкт-Петербург', 'diff': 0},
    # ... остальные регионы ...
}

async def search_companies(params, per_page=100, max_api_pages=20):
    url = "https://api.hh.ru/employers"
    headers = {"User-Agent": "api-test-agent"}
    page = params.get('page', 1)
    result = []
    total_found = 0
    api_page = 0
    skip = (page - 1) * per_page
    filtered_count = 0
    industry_val = params.get("industry_manual").strip() if params.get("industry_manual") else params.get("industry")
    async with httpx.AsyncClient() as client:
        while api_page < max_api_pages and len(result) < per_page:
            query = {"per_page": 100, "page": api_page, "only_with_vacancies": True, "sort_by": "by_vacancies_open"}
            area_val = params.get("area_manual") or params.get("area")
            if area_val: query["area"] = area_val
            if industry_val: query["industry"] = industry_val
            try:
                response = await client.get(url, headers=headers, params=query)
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
                            details_resp = await client.get(f"https://api.hh.ru/employers/{emp['id']}", headers=headers)
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
            except httpx.RequestError as e:
                print(f"Ошибка при получении компаний: {e}")
                break
            api_page += 1
    return result, total_found

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    params = {"keyword": '', "area": '', "area_manual": '', "industry": '', "industry_manual": '', "page": 1}
    page = 1
    per_page = 100
    companies = None
    total = 0
    total_pages = 1
    return templates.TemplateResponse("index.html", {
        "request": request,
        "companies": companies,
        "total": total,
        "params": params,
        "area_options": AREA_OPTIONS,
        "page": page,
        "total_pages": total_pages,
        "REGION_TIMEZONES": REGION_TIMEZONES
    })

@app.post("/", response_class=HTMLResponse)
async def index_post(request: Request, 
    area: str = Form(''),
    area_manual: str = Form(''),
    page: int = Form(1)
):
    params = {"keyword": '', "area": area, "area_manual": area_manual, "industry": '', "industry_manual": '', "page": page}
    per_page = 100
    companies, total = await search_companies(params, per_page=per_page)
    total_pages = math.ceil(total / per_page) if total else 1
    return templates.TemplateResponse("index.html", {
        "request": request,
        "companies": companies,
        "total": total,
        "params": params,
        "area_options": AREA_OPTIONS,
        "page": page,
        "total_pages": total_pages,
        "REGION_TIMEZONES": REGION_TIMEZONES
    }) 