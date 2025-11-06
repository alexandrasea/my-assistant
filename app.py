


# app.py (FastAPI)
from fastapi import FastAPI
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer
import faiss, numpy as np

app = FastAPI()
embedder = SentenceTransformer("all-MiniLM-L6-v2")

# Военно опростено: държим всичко в памет за MVP
 # Примерни данни за да има какво да мачваме
ITEMS = [
    {
        "id": 1, "type": "program",
        "title": "Графичен дизайн – бакалавър",
        "text": "Програма по визуални изкуства, типография, композиция, цветознание, бранд идентичност.",
        "skills_required": ["рисуване", "креативност", "Adobe Photoshop", "илюстрация"],
        "language": "bulgarian",
        "location": "Sofia",
        "tuition": 3000
    },
    {
        "id": 2, "type": "program",
        "title": "Маркетинг и комуникации – бакалавър",
        "text": "Стратегически маркетинг, дигитални канали, съдържание, PR и бранд мениджмънт.",
        "skills_required": ["комуникация", "copywriting", "социални мрежи"],
        "language": "bulgarian",
        "location": "Sofia",
        "tuition": 2800
    },
    {
        "id": 3, "type": "program",
        "title": "Изящни изкуства – живопис",
        "text": "Академично рисуване, живопис, история на изкуството, художествени техники.",
        "skills_required": ["рисуване", "живопис", "креативност"],
        "language": "bulgarian",
        "location": "Remote",
        "tuition": 2500
    },
    {
        "id": 4, "type": "job",
        "title": "Junior Graphic Designer",
        "text": "Работа по печатни и дигитални материали, банери, постове. Работа с арт директор.",
        "skills_required": ["Photoshop", "Illustrator", "композиция", "креативност"],
        "language": "bulgarian",
        "location": "Sofia",
        "salary_min": 1800
    },
    {
        "id": 5, "type": "job",
        "title": "Junior Marketing Associate",
        "text": "Създаване на съдържание, кампании в социални мрежи, анализ на резултати.",
        "skills_required": ["комуникация", "социални мрежи", "copywriting"],
        "language": "bulgarian",
        "location": "Hybrid",
        "salary_min": 1600
    },
    {
        "id": 6, "type": "job",
        "title": "Учител по изобразително изкуство (частно училище)",
        "text": "Подготовка на уроци, работа с ученици, развиване на художествени умения.",
        "skills_required": ["рисуване", "комуникация", "търпение"],
        "language": "bulgarian",
        "location": "Sofia",
        "salary_min": 1500
    },
]

ITEM_VECS = None

def _build_index():
    global ITEM_VECS
    # правим текст за векторизация от заглавие + описание + умения
    texts = []
    for it in ITEMS:
        skills = ", ".join(it.get("skills_required", []))
        t = f"{it['title']} {it.get('text','')} skills:{skills} type:{it['type']} location:{it.get('location','')}"
        texts.append(t)
    vecs = embedder.encode(texts, convert_to_numpy=True)
    norms = np.linalg.norm(vecs, axis=1, keepdims=True) + 1e-10
    ITEM_VECS = vecs / norms

# построяваме индекс при стартиране на сървъра
_build_index()
     

class Profile(BaseModel):
    goal: str                  # "job" или "program"
    level: str
    interests: list[str]
    skills_strong: list[str]
    skills_current: list[str]
    location: str
    language: str
    mode: str                  # online/onsite/hybrid
    budget_max: int | None = None
    salary_min: int | None = None

def hard_filters(item, p: Profile):
    if p.goal == "job" and item["type"] != "job": return False
    if p.goal == "program" and item["type"] != "program": return False
    if p.language and item.get("language") and p.language.lower() not in item["language"].lower(): return False
    if p.goal == "job" and p.salary_min and item.get("salary_min") and item["salary_min"] < p.salary_min: return False
    if p.goal == "program" and p.budget_max and item.get("tuition") and item["tuition"] > p.budget_max: return False
    return True

@app.post("/match")
def match(p: Profile):
    # 1) филтър
    candidates = [it for it in ITEMS if hard_filters(it, p)]
    if not candidates:
        return {"matches": []}

    # 2) вектор на профила
    profile_text = " ".join([
        f"goal:{p.goal}", f"level:{p.level}",
        "interests:" + ", ".join(p.interests),
        "strong:" + ", ".join(p.skills_strong),
        "current:" + ", ".join(p.skills_current)
    ])
    uvec = embedder.encode([profile_text], convert_to_numpy=True)
    uvec = uvec / np.linalg.norm(uvec)

    # 3) подобие и смесена метрика
    # (тук за простота само cosine върху описание)
    item_inds = [ITEMS.index(c) for c in candidates]
    ivecs = ITEM_VECS[item_inds]
    ivecs = ivecs / np.linalg.norm(ivecs, axis=1, keepdims=True)
    sims = (ivecs @ uvec.T).ravel()

    scored = []
    for c, s in zip(candidates, sims):
        loc_bonus = 1.0 if p.location and p.location.lower() in (c.get("location","").lower()+" remote") else 0.8
        lang_bonus = 1.0 if not p.language or not c.get("language") or p.language.lower() in c["language"].lower() else 0.6
        score = 0.8*s + 0.1*loc_bonus + 0.1*lang_bonus
        scored.append((score, c))

    scored.sort(key=lambda x: x[0], reverse=True)
    return {"matches": [{"score": float(sc), "item": it} for sc, it in scored[:10]]}

