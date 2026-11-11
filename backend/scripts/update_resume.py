import sys
from pathlib import Path
import json
import sqlite3

sys.path.insert(0, "backend")
from app.services.documents import extract_text
from app.services.structured_parser import parse_resume_document

def run():
    for db_path in ["data/recruitment.db", "backend/data/recruitment.db"]:
        p_db = Path(db_path)
        if not p_db.exists():
            continue
        con = sqlite3.connect(p_db)
        cur = con.cursor()
        rows = cur.execute('SELECT id, storage_key FROM resume_versions WHERE id="3ab8c875-d2dc-49d2-bccf-686acbe7174c"').fetchall()
        for r_id, s_key in rows:
            f_path = Path("storage") / s_key
            if not f_path.exists():
                f_path = Path("backend/storage") / s_key
            if f_path.exists():
                text = extract_text(f_path)
                data = parse_resume_document(text)
                cur.execute(
                    "UPDATE resume_extractions SET extraction_json=?, model_id=? WHERE resume_version_id=?",
                    (json.dumps(data), "structured-document-parser-v3 (HF 402 Fallback)", r_id)
                )
                con.commit()
                print(f"Updated {db_path} for {r_id} with full structured JSON!")
        con.close()

if __name__ == "__main__":
    run()
