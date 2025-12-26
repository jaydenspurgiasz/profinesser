from dataclasses import dataclass
from typing import Optional

@dataclass
class Faculty:
    name: str
    id: str
    h_index: int
    specialty: str
    top_paper: str
    last_known_institution: str
    orcid: Optional[str] = None
    works_count: int = 0
    total_citations: int = 0
    impact_score: float = 0.0 # 2-year mean citedness
    
    def __repr__(self):
        return f"<Faculty: {self.name} | Focus: {self.specialty} | Recency score: {self.impact_score}>"
