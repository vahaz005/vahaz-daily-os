from typing import List, Optional, TypedDict

class NewsletterState(TypedDict):
    date: str
    topics: List[str]
    raw_research: str
    draft: str
    rewrite_count: int
    score: int
    critique: str
    approved: bool
    final_html: str
    sent: bool
    error: Optional[str]
