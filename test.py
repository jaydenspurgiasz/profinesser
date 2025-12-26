from FacultyAgent import FacultyAgent
from BaseStorage import SQLiteStorage

db = SQLiteStorage()
FAgent = FacultyAgent(db)




keywords = ["Fair division", "Combinatorics", "Graph Neural Networks"]

results = FAgent.get_experts("UCLA", keywords)
print(results)
