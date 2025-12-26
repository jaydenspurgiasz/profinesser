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
        # 1. Resolve Institution ID
        inst_res = requests.get(f"{self.base_url}/institutions", 
                                params={"search": school_name}, headers=self.headers).json()
        if not inst_res['results']: return []
        school_id = inst_res['results'][0]['id']
        school_display = inst_res['results'][0]['display_name']

        # 2. Search for WORKS (The "OR" logic)
        works_params = {
            "filter": f"institutions.id:{school_id}",
            "search": " OR ".join(f'"{kw}"' for kw in keywords),
            "sort": "cited_by_count:desc",
            "per_page": 50
        }
        works_data = requests.get(f"{self.base_url}/works", params=works_params, headers=self.headers).json()
        
        # 3. Aggregate Authors
        author_scores = {}
        for work in works_data.get('results', []):
            for authorship in work.get('authorships', []):
                if any(inst.get('id') == school_id for inst in authorship.get('institutions', [])):
                    a_id = authorship.get('author', {}).get('id')
                    if a_id:
                        if a_id not in author_scores:
                            author_scores[a_id] = {"top_paper": work.get('title'), "count": 1}
                        else:
                            author_scores[a_id]["count"] += 1

        top_ids = list(author_scores.keys())[:25]
        if not top_ids: return []

        # 4. Fetch Enriched Profiles (Broadened Field Logic)
        verified_list = []
        author_res = requests.get(f"{self.base_url}/authors", 
                                 params={"filter": f"id:{'|'.join(top_ids)}"}, headers=self.headers).json()

        for author in author_res.get('results', []):
            topics = author.get('topics', [])
            stats = author.get('summary_stats', {})
            ids = author.get('ids', {})
            
            # Primary research Topic/Field
            primary_topic = topics[0].get('display_name') if topics else "General Research"
            primary_field = topics[0].get('field', {}).get('display_name') if topics else "N/A"

            verified_list.append(Faculty(
                name=author['display_name'],
                id=author['id'],
                h_index=stats.get('h_index', 0),
                specialty=f"{primary_field}: {primary_topic}", # Shows the field dynamically
                top_paper=author_scores[author['id']]['top_paper'],
                last_known_institution=school_display,
                orcid=ids.get('orcid'),
                works_count=author.get('works_count', 0),
                total_citations=author.get('cited_by_count', 0),
                impact_score=stats.get('2yr_mean_citedness', 0.0)
            ))

        # 5. Sort by Impact and Return
        results = sorted(verified_list, key=lambda x: (x.h_index, x.impact_score), reverse=True)[:limit]
        self.storage.save_faculty(results)
        return results

