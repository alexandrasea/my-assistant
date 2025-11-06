# ui.py — прост уеб интерфейс към FastAPI /match
import streamlit as st
import requests

API_URL = "http://127.0.0.1:8000/match"

st.set_page_config(page_title="Career/Uni Assistant", layout="centered")
st.title("🎯 Асистент за работа или университет")

with st.form("profile_form"):
    col1, col2 = st.columns(2)
    with col1:
        goal = st.selectbox("Цел", ["работа", "университет"])
        level = st.text_input("Ниво (напр. junior / bachelor)")
        location = st.text_input("Локация (напр. Sofia / Remote)")
        language = st.text_input("Език (напр. english / bulgarian)")
        mode = st.selectbox("Режим", ["online", "onsite", "hybrid", "remote"])
    with col2:
        interests = st.text_input("Интереси (разделени със запетаи)")
        skills_strong = st.text_input("Силни умения (до 5, със запетаи)")
        skills_current = st.text_input("Текущи умения (до 10, със запетаи)")
        budget_max = st.text_input("Бюджет макс (за програми, празно ако няма)")
        salary_min = st.text_input("Минимална заплата (за работа, празно ако няма)")

    submitted = st.form_submit_button("Намери предложения")

if submitted:
    payload = {
        "goal": goal,
        "level": level or "",
        "interests": [s.strip() for s in interests.split(",") if s.strip()],
        "skills_strong": [s.strip() for s in skills_strong.split(",") if s.strip()],
        "skills_current": [s.strip() for s in skills_current.split(",") if s.strip()],
        "location": location or "",
        "language": language or "",
        "mode": mode,
        "budget_max": int(budget_max) if budget_max.strip().isdigit() else None,
        "salary_min": int(salary_min) if salary_min.strip().isdigit() else None,
    }
    with st.spinner("Мисля..."):
        try:
            r = requests.post(API_URL, json=payload, timeout=60)
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            st.error(f"Проблем с бекенда: {e}")
            st.stop()

    matches = data.get("matches", [])
    if not matches:
        st.info("Няма резултати за тези критерии. Пробвай да разшириш търсенето.")
    else:
        st.subheader("Топ предложения")
        for m in matches:
            score = m.get("score", 0)
            it = m.get("item", {})
            st.markdown(f"### {it.get('title','(без заглавие)')} — {it.get('org','')}")
            st.write(
                f"**Тип:** {it.get('type')}  |  **Локация:** {it.get('location','–')}  |  "
                f"**Език:** {it.get('language','–')}  |  **Режим:** {it.get('mode','–')}"
            )
            if it.get("salary_min") is not None:
                st.write(f"**Заплата от:** {it['salary_min']}")
            if it.get("tuition") is not None:
                st.write(f"**Такса:** {it['tuition']}")
            skills = ", ".join(it.get("skills_required", []))
            st.write(f"**Изисквани умения:** {skills or '–'}")
            st.progress(min(max(score, 0.0), 1.0))  # визуализация на score (0..1)
            st.divider()

st.caption("Подкарай бекенда на http://127.0.0.1:8000 и зареди items.json за реални резултати.")
