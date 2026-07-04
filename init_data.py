from db import init_db, seed_companies
from pathlib import Path
import json

init_db()

companies = [
    {"name":"TCS", "required_skills":["java","sql","communication"], "min_cgpa":6.5},
    {"name":"Infosys", "required_skills":["java","data-structures","problem solving"], "min_cgpa":7.0},
    {"name":"Wipro", "required_skills":["python","sql","automation"], "min_cgpa":6.5},
    {"name":"Google-Intern", "required_skills":["python","algorithms","system design"], "min_cgpa":8.5},
    {"name":"Accenture", "required_skills":["c#",".net","sql"], "min_cgpa":6.0},
]

seed_companies(companies)

# create tests folder and aptitude file
tests_dir = Path("tests")
tests_dir.mkdir(exist_ok=True)
apt = {
    "title":"Aptitude Test (Sample)",
    "questions":[
        {"q":"If 5x=20, x = ?", "options":["2","4"], "answer":"4"},
        {"q":"12% of 50 is?", "options":["6","60"], "answer":"6"},
        {"q":"Next in series 2,4,8,16?", "options":["32","24"], "answer":"32"}
    ]
}
(test_file := tests_dir / "aptitude.json").write_text(json.dumps(apt, indent=2))
print("Initialized DB and created tests/aptitude.json")
print("Put your 3 downloadable company papers (PDF) into the folder: papers/")