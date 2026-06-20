import json
import os
import re
import datetime

MEMORY_FILE = "editions/memory.json"

def _load_all() -> dict:
    if not os.path.exists(MEMORY_FILE):
        return {}
    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def _extract_headings(text: str) -> list:
    if not text:
        return []
    return [h.strip() for h in re.findall(r"^##\s+(.+)$", text, re.MULTILINE)]

def save_to_memory(state: dict):
    memory = _load_all()
    date = state.get("date")
    if not date:
        return
    
    draft = state.get("draft", "")
    headings = _extract_headings(draft)
    
    memory[date] = {
        "topics": state.get("topics", []),
        "score": state.get("score", 0),
        "headings": headings
    }
    
    os.makedirs(os.path.dirname(MEMORY_FILE), exist_ok=True)
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(memory, f, indent=4)

def load_recent_memory(days=7) -> str:
    memory = _load_all()
    if not memory:
        return "No recent editions in memory."
    
    today = datetime.date.today()
    recent_entries = []
    for date_str, info in sorted(memory.items(), reverse=True):
        try:
            entry_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
            if (today - entry_date).days <= days:
                recent_entries.append((date_str, info))
        except ValueError:
            continue
    
    if not recent_entries:
        return f"No recent editions in the last {days} days."
    
    lines = []
    for date_str, info in recent_entries:
        topics_str = ", ".join(info.get("topics", []))
        headings_str = ", ".join(info.get("headings", []))
        score = info.get("score", 0)
        lines.append(
            f"Date: {date_str} (Score: {score})\n"
            f"  Topics: {topics_str}\n"
            f"  Headings: {headings_str}"
        )
    return "\n\n".join(lines)
