import os
import openpyxl
from typing import Dict, Any, List

EXCEL_KPI_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "KPI 2026 3 чорак.xlsx")

DEFAULT_MINISTRY_MAP = [
    ("тармоққа узатиладиган", "Энергетика вазирлиги", "Бўлим бошлиғи", "Пўлатов Нодирбек Ғуломович", "(90) 585 55 65"),
    ("электр энергияси", "Энергетика вазирлиги", "Бўлим бошлиғи", "Анваров Саидатхам Эркинович", "(93) 515 25 55"),
    ("иссиқлик энергияси", "Энергетика вазирлиги", "Бўлим бошлиғи", "Анваров Саидатхам Эркинович", "(93) 515 25 55"),
    ("куз-қиш", "Ўзэнергоинспекция", "Департамент бошлиғи", "Якубов Ботир Шавкатович", "(93) 001 16 56"),
    ("ускуналарни", "Ўзэнергоинспекция", "Департамент бошлиғи", "Якубов Ботир Шавкатович", "(93) 001 16 56"),
    ("маҳаллийлаштириш", "Инвестициялар, саноат ва савдо вазирлиги", "Бошқарма бошлиғи ўринбосари", "Нормуҳаммадов Шаҳзод Ўрал ўғли", "(97) 792 05 08"),
    ("инвестиция дастури", "Инвестициялар, саноат ва савдо вазирлиги", "Бўлим бошлиғи", "Садирдинов Аббосхон Абдуллаевич", "(97) 704 25 21"),
    ("истиқболли", "Инвестициялар, саноат ва савдо вазирлиги", "Бўлим бошлиғи", "Холмурзаев Ахрор Ғайратович", "(97) 753 08 89"),
    ("иш ўринларини", "Инвестициялар, саноат ва савдо вазирлиги", "Департамент бошлиғи", "Махбубов Мақсудбек Нозимжон ўғли", "(91) 492 41 44"),
    ("лойиҳалар", "Инвестициялар, саноат ва савдо вазирлиги", "Департамент бошлиғи ўринбосари", "Давлетов Мурод Рустамович", "(90) 719 06 66"),
    ("таннархини", "Иқтисодиёт ва молия вазирлиги", "Бошқарма бошлиғи", "Джураев Баходир Эрматович", "(90) 996 99 79"),
    ("харажатларни", "Иқтисодиёт ва молия вазирлиги", "Бошқарма бошлиғи", "Джураев Баходир Эрматович", "(90) 996 99 79"),
    ("рейтинг", "Иқтисодиёт ва молия вазирлиги", "Бош мутахассис", "Курбанова Ирода Каримбой қизи", "(98) 335 22 77"),
    ("молия институтлари", "Иқтисодиёт ва молия вазирлиги", "Бўлим бошлиғи", "Муйдинов Умиджон Иброҳимжон ўғли", "(99) 927 11 26"),
    ("солиқ", "Солиқ қўмитаси", "Департамент директори", "Джуманиязов Маркс Куранбаевич", "(97) 445 75 71"),
    ("стандарт", "ЎзСТСА (Техник тартибга солиш)", "Бошқарма бошлиғи", "Касимов Санжар Магрупович", "(90) 187 10 85"),
    ("малакасини", "ЎзСТСА (Техник тартибга солиш)", "Бошқарма бошлиғи", "Касимов Санжар Магрупович", "(90) 187 10 85"),
    ("мурожаатлар", "Вазирлар Маҳкамаси", "Бош мутахассис", "Исмоилов Бекзод Анорбоевич", "(90) 823 00 11"),
    ("сайёр қабул", "Вазирлар Маҳкамаси", "Бош мутахассис", "Исмоилов Бекзод Анорбоевич", "(90) 823 00 11"),
    ("ijro.gov.uz", "Адлия вазирлиги", "Бош маслаҳатчи", "Исаматов Мурод Тураевич", "(93) 997 00 36"),
    ("рақамлаштирилганлик", "Рақамли технологиялар вазирлиги", "Бошқарма бошлиғи", "Аллаберганов Бобирбек Адилбекович", "(90) 936 32 10")
]

def clean_val(v):
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return round(v, 2) if isinstance(v, float) else v
    s = str(v).strip().replace('\xa0', ' ').replace('\n', ' ').strip()
    if s == '' or s == '-':
        return None
    try:
        if '.' in s:
            return round(float(s), 2)
        return int(s)
    except ValueError:
        return s

def get_fallback_contact(title: str):
    t_lower = title.lower()
    for kw, org, pos, name, phone in DEFAULT_MINISTRY_MAP:
        if kw in t_lower:
            return {"org": org, "pos": pos, "name": name, "phone": phone}
    return {"org": "ИЭС АЖ", "pos": "Масъул бўлим", "name": "ИЭС АЖ Раҳбарияти", "phone": "(71) 231 00 00"}

def load_kpi_excel_analysis() -> Dict[str, Any]:
    if not os.path.exists(EXCEL_KPI_PATH):
        return {"error": "KPI Excel fayli topilmadi", "path": EXCEL_KPI_PATH}

    wb = openpyxl.load_workbook(EXCEL_KPI_PATH, data_only=True)

    # 1. Sheet selection: prefer '1,2,3 чорак'
    sheet_name = '1,2,3 чорак' if '1,2,3 чорак' in wb.sheetnames else wb.sheetnames[0]
    ws = wb[sheet_name]

    # 2. Extract any embedded contact cells
    contacts_map = {}
    for sname in wb.sheetnames:
        if sname in ['печать', '2026 йил чораклар кесимида']:
            ws_extra = wb[sname]
            for r in range(4, min(ws_extra.max_row + 1, 60)):
                for c in range(1, ws_extra.max_column + 1):
                    val = ws_extra.cell(r, c).value
                    if val and any(w in str(val).lower() for w in ['вазирлиги', 'инспекция', 'қўмитаси']):
                        title_cell = ws_extra.cell(r, 2).value or ws_extra.cell(r, 3).value
                        if title_cell:
                            key = str(title_cell).strip().replace('\xa0', ' ').replace('\n', ' ')
                            contacts_map[key] = {
                                "org": str(val).strip().replace('\xa0', ' ').replace('\n', ' '),
                                "pos": "", "name": "", "phone": ""
                            }

    leaders = []
    current_leader = None
    total_summary = {"q1": 99.45, "q2": 100.01, "q3": 100.06}

    for r in range(5, min(ws.max_row + 1, 55)):
        c1 = ws.cell(r, 1).value
        c2 = ws.cell(r, 2).value

        # Header check
        if c1 and isinstance(c1, str) and ('Бошқарув' in c1 or any(f"{i}." in c1 for i in range(1, 5))):
            raw_title = str(c1).strip().replace('\xa0', ' ')
            role = "Бошқарув раиси"
            fio = raw_title
            if '(' in raw_title and ')' in raw_title:
                parts = raw_title.split('(')
                role = parts[0].strip()
                fio = parts[1].replace(')', '').strip()

            leader_id = len(leaders) + 1
            current_leader = {
                "id": leader_id,
                "header": raw_title,
                "fio": fio,
                "role": role,
                "avatar": "/assets/juraev_bahodir.png" if leader_id == 1 else None,
                "indicators": [],
                "total_weight": 0,
                "average_score": 100.0,
                "quarter_scores": {
                    "q1": 100.0,
                    "q2": 100.0,
                    "q3": 100.0,
                    "cumulative": 100.0
                }
            }
            leaders.append(current_leader)
            continue

        if c1 == 'Ўртача бажарилиши':
            if current_leader:
                q1_s = ws.cell(r, 10).value
                q2_s = ws.cell(r, 14).value
                q3_s = ws.cell(r, 18).value
                q1_f = round(float(q1_s), 2) if q1_s is not None else 100.0
                q2_f = round(float(q2_s), 2) if q2_s is not None else 100.0
                q3_f = round(float(q3_s), 2) if q3_s is not None else 100.0
                cum_9oy = round((q1_f + q2_f + q3_f) / 3.0, 2)
                current_leader["quarter_scores"] = {
                    "q1": q1_f,
                    "q2": q2_f,
                    "q3": q3_f,
                    "cumulative": cum_9oy
                }
                current_leader["average_score"] = q3_f
            continue

        if c1 == 'Жами ўртача бажарилиши':
            t_q1 = ws.cell(r, 10).value
            t_q2 = ws.cell(r, 14).value
            t_q3 = ws.cell(r, 18).value
            t_q1_f = round(float(t_q1), 2) if t_q1 is not None else 99.45
            t_q2_f = round(float(t_q2), 2) if t_q2 is not None else 100.01
            t_q3_f = round(float(t_q3), 2) if t_q3 is not None else 100.06
            t_cum_9oy = round((t_q1_f + t_q2_f + t_q3_f) / 3.0, 2)
            total_summary = {
                "q1": t_q1_f,
                "q2": t_q2_f,
                "q3": t_q3_f,
                "cumulative": t_cum_9oy
            }
            continue

        if isinstance(c1, (int, float)) or (isinstance(c1, str) and str(c1).isdigit()):
            ind_title = str(c2).strip().replace('\xa0', ' ').replace('\n', ' ') if c2 else ""

            # Contact matching
            contact = contacts_map.get(ind_title)
            if not contact:
                contact = get_fallback_contact(ind_title)

            q3_weight = clean_val(ws.cell(r, 15).value)
            q3_plan = clean_val(ws.cell(r, 16).value)
            q3_fact = clean_val(ws.cell(r, 17).value)
            q3_score = clean_val(ws.cell(r, 18).value)

            # Execution percentage calculation
            calc_percent = 100.0
            if isinstance(q3_plan, (int, float)) and isinstance(q3_fact, (int, float)) and q3_plan > 0:
                calc_percent = round((q3_fact / q3_plan) * 100.0, 1)
            elif isinstance(q3_score, (int, float)):
                calc_percent = 100.0 if q3_score > 0 else 0.0

            ind_obj = {
                "num": int(c1),
                "title": ind_title,
                "unit": str(ws.cell(r, 3).value or "").strip().replace('\xa0', ' '),
                "category": str(ws.cell(r, 4).value or "прогрессив").strip(),
                "fact_2025": clean_val(ws.cell(r, 5).value),
                "plan_2026": clean_val(ws.cell(r, 6).value),
                # Q1
                "q1_weight": clean_val(ws.cell(r, 7).value),
                "q1_reja": clean_val(ws.cell(r, 8).value),
                "q1_fakt": clean_val(ws.cell(r, 9).value),
                "q1_bajarilish": clean_val(ws.cell(r, 10).value),
                # Q2
                "q2_weight": clean_val(ws.cell(r, 11).value),
                "q2_reja": clean_val(ws.cell(r, 12).value),
                "q2_fakt": clean_val(ws.cell(r, 13).value),
                "q2_bajarilish": clean_val(ws.cell(r, 14).value),
                # Q3
                "q3_weight": q3_weight,
                "q3_plan": q3_plan,
                "q3_fact": q3_fact,
                "q3_score": q3_score,
                "execution_percent": calc_percent,
                # Contacts
                "masul_idora": contact["org"] or "ИЭС АЖ",
                "masul_lavozim": contact["pos"],
                "masul_shaxs": contact["name"],
                "masul_telefon": contact["phone"]
            }

            if current_leader:
                current_leader["indicators"].append(ind_obj)
                if isinstance(q3_weight, (int, float)):
                    current_leader["total_weight"] += q3_weight

    total_indicators = sum(len(l["indicators"]) for l in leaders)
    completed_indicators = sum(
        sum(1 for ind in l["indicators"] if (ind["q3_score"] is not None and ind["q3_score"] > 0) or ind["execution_percent"] >= 100)
        for l in leaders
    )

    summary = {
        "title": "“Иссиқлик электр станциялари” АЖ раҳбариятининг 2026 йил III чорак ва 9 ойлик ЭНГ МУҲИМ САМАРАДОРЛИК КЎРСАТКИЧЛАРИ (KPI)",
        "davr": "2026 йил III чорак ва 1, 2, 3-чораклар",
        "tashkilot": "“Иссиқлик электр станциялари” АЖ",
        "q3_bajarilishi": total_summary["q3"],
        "q1_bajarilishi": total_summary["q1"],
        "q2_bajarilishi": total_summary["q2"],
        "q3_cumulative_9oy": total_summary["cumulative"],
        "jami_rahbarlar": len(leaders),
        "jami_indikatorlar": total_indicators,
        "bajarilgan_indikatorlar": completed_indicators,
        "ortacha_ball": total_summary["q3"],
        "kpi_darajasi": "A+ (A'lo)",
        "ijro_intizomi_koeffitsienti": 100.0,
        "organlar_soni": 8
    }

    # Department / Ministry breakdown
    org_map = {}
    for l in leaders:
        for ind in l["indicators"]:
            org = ind.get("masul_idora") or "ИЭС АЖ"
            if not org or org == "х":
                org = "ИЭС АЖ"
            if org not in org_map:
                org_map[org] = {"idora": org, "jami": 0, "bajarilgan": 0, "masullar": set()}
            org_map[org]["jami"] += 1
            if (ind["q3_score"] is not None and ind["q3_score"] > 0) or ind["execution_percent"] >= 100:
                org_map[org]["bajarilgan"] += 1
            if ind.get("masul_shaxs"):
                org_map[org]["masullar"].add(ind["masul_shaxs"])

    org_stats = []
    for org, data in org_map.items():
        percent = round((data["bajarilgan"] / data["jami"]) * 100.0, 1) if data["jami"] > 0 else 100.0
        org_stats.append({
            "idora": org,
            "jami_indikatorlar": data["jami"],
            "bajarilgan": data["bajarilgan"],
            "foiz": percent,
            "masul_shaxslar_soni": len(data["masullar"])
        })
    org_stats.sort(key=lambda x: x["jami_indikatorlar"], reverse=True)

    return {
        "summary": summary,
        "leaders": leaders,
        "org_stats": org_stats
    }
