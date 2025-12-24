import requests
from typing import List, Optional
from BaseStorage import BaseStorage
from DataTypes import Faculty


class FacultyAgent:
    def __init__(self, storage: BaseStorage, email: Optional[str] = None):
        self.storage = storage
        self.base_url = "https://api.openalex.org"
        # Flexible User-Agent: Uses Polite Pool if email provided, otherwise standard
        agent_str = f"FacultyAgent/1.0 (mailto:{email})" if email else "FacultyAgent/1.0"
        self.headers = {"User-Agent": agent_str}

    def get_experts(self, school_name: str, keywords: List[str], limit: int = 10) -> List[Faculty]:
        # 1. Resolve Institution ID (Always reliable)
        inst_res = requests.get(f"{self.base_url}/institutions", 
                                params={"search": school_name}, headers=self.headers).json()
        if not inst_res['results']: return []
        school_id = inst_res['results'][0]['id']
        school_display = inst_res['results'][0]['display_name']

        # 2. Search for WORKS (The "OR" logic)
        # Using "search" finds keywords in title, abstract, or concepts
        works_params = {
            "filter": f"institutions.id:{school_id}",
            "search": " OR ".join(f'"{kw}"' for kw in keywords), # Force OR logic
            "sort": "cited_by_count:desc",
            "per_page": 50
        }
        works_data = requests.get(f"{self.base_url}/works", params=works_params, headers=self.headers).json()
        
        # 3. Aggregate Authors from those papers
        # This identifies who is actually doing the work
        author_scores = {} # author_id -> {details}
        for work in works_data.get('results', []):
            for authorship in work.get('authorships', []):
                # Filter for authors specifically at this school
                is_at_school = any(inst.get('id') == school_id for inst in authorship.get('institutions', []))
                if is_at_school:
                    a_id = authorship.get('author', {}).get('id')
                    if a_id and a_id not in author_scores:
                        author_scores[a_id] = {
                            "name": authorship['author']['display_name'],
                            "top_paper": work.get('title'),
                            "count": 1
                        }
                    elif a_id:
                        author_scores[a_id]["count"] += 1

        # 4. Fetch Profiles and filter for Technical Fields
        # We only take the authors who appeared most in our search
        top_ids = list(author_scores.keys())[:20]
        if not top_ids: return []

        verified_list = []
        author_res = requests.get(f"{self.base_url}/authors", 
                                 params={"filter": f"id:{'|'.join(top_ids)}"}, headers=self.headers).json()

        technical_fields = ["Computer Science", "Mathematics", "Engineering"]
        for author in author_res.get('results', []):
            topics = author.get('topics', [])
            # Only keep them if they belong to a technical field
            is_technical = any(t.get('field', {}).get('display_name') in technical_fields for t in topics[:3])
            
            if is_technical:
                verified_list.append(Faculty(
                    name=author['display_name'],
                    id=author['id'],
                    h_index=(author.get('summary_stats') or {}).get('h_index', 0),
                    specialty=topics[0].get('display_name') if topics else "Researcher",
                    top_paper=author_scores[author['id']]['top_paper'],
                    last_known_institution=school_display
                ))

        # 5. Commit and Return
        results = sorted(verified_list, key=lambda x: x.h_index, reverse=True)[:limit]
        self.storage.save_faculty(results)
        return results