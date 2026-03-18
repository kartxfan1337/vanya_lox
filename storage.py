import json
import os
import uuid
from typing import List, Dict, Optional

DATA_FILE = os.environ.get("DATA_FILE", "portfolio_data.json")


class PortfolioStorage:
    def __init__(self):
        self._data = self._load()

    def _load(self) -> dict:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _save(self):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)

    def _user(self, user_id: str) -> dict:
        if user_id not in self._data:
            self._data[user_id] = {"projects": [], "skills": []}
        return self._data[user_id]

    # ── Projects ──────────────────────────────────────────────────────────────

    def get_projects(self, user_id: str) -> List[Dict]:
        return self._user(user_id)["projects"]

    def get_project(self, user_id: str, project_id: str) -> Optional[Dict]:
        for p in self._user(user_id)["projects"]:
            if p["id"] == project_id:
                return p
        return None

    def add_project(self, user_id: str, project: dict):
        project["id"] = str(uuid.uuid4())[:8]
        self._user(user_id)["projects"].append(project)
        self._save()

    def update_project(self, user_id: str, project_id: str, updates: dict):
        for p in self._user(user_id)["projects"]:
            if p["id"] == project_id:
                p.update(updates)
                break
        self._save()

    def delete_project(self, user_id: str, project_id: str):
        user = self._user(user_id)
        user["projects"] = [p for p in user["projects"] if p["id"] != project_id]
        self._save()

    # ── Skills ────────────────────────────────────────────────────────────────

    def get_skills(self, user_id: str) -> List[str]:
        return self._user(user_id)["skills"]

    def add_skills(self, user_id: str, skills: List[str]):
        existing = set(self._user(user_id)["skills"])
        for s in skills:
            if s not in existing:
                self._user(user_id)["skills"].append(s)
                existing.add(s)
        self._save()

    def delete_skill(self, user_id: str, skill: str):
        user = self._user(user_id)
        user["skills"] = [s for s in user["skills"] if s != skill]
        self._save()
