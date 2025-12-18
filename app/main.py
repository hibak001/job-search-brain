import streamlit as st
import os
from core.extract_text import extract_text
from core.db import init_db
from core.db import init_db, add_document, list_resumes
from core.db import init_db, add_document, list_resumes, add_job, add_application, list_jobs, get_resume_for_job

import re

def parse_company_role(message: str):
    """
    Very simple parser.
    Tries to extract: company and role from common phrasing.
    Returns (company, role) or (None, None).
    """
    msg = message.strip()

    # Pattern: "... for <company> <role>" or "... for <company> - <role>"
    m = re.search(r"\bfor\s+(.+)$", msg, flags=re.IGNORECASE)
    if not m:
        return None, None

    tail = m.group(1).strip()

    # If user uses separators like "-" or "|"
    if " - " in tail:
        company, role = tail.split(" - ", 1)
        return company.strip(), role.strip()
    if " | " in tail:
        company, role = tail.split(" | ", 1)
        return company.strip(), role.strip()

    # Otherwise try: first word chunk = company, rest = role (works ok for many cases)
    parts = tail.split()
    if len(parts) < 2:
        return None, None

    company = parts[0]
    role = " ".join(parts[1:])
    return company.strip(), role.strip()




st.set_page_config(page_title="Job Search Brain", layout="wide")
st.title("Job Search Brain 🤖")
init_db()

tab_upload, tab_add_app, tab_history, tab_chat = st.tabs(["Upload", "Add Application", "History", "Chatbot"])

with tab_upload:
    st.subheader("Upload documents")

    doc_type = st.selectbox(
        "What are you uploading?",
        ["Resume", "Job Description", "Cover Letter", "Notes"]
    )

    doc_type_map = {
        "Resume": "resume",
        "Job Description": "jd",
        "Cover Letter": "cover_letter",
        "Notes": "notes",
    }
    doc_type_db = doc_type_map[doc_type]


    uploaded_file = st.file_uploader(
        "Upload a file (PDF or DOCX)",
        type=["pdf", "docx"]
    )

    UPLOAD_DIR = "data/uploads"
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    if uploaded_file:
        save_path = os.path.join(UPLOAD_DIR, uploaded_file.name)

        with open(save_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        st.success(f"Saved file to {save_path}")

        doc_id = add_document(doc_type_db, uploaded_file.name, save_path)
        st.caption(f"Document saved in DB with id: {doc_id}")

        try:
            text = extract_text(save_path)

            # ✅ 1) Quick proof: how much text was extracted
            st.caption(f"Extracted characters: {len(text)}")

            # ✅ 2) Your existing preview (first part only)
            st.subheader("Extracted text preview")
            st.text_area("Preview", text[:2000], height=250)

            # ✅ 3) Proof of completeness: show the end of the document
            st.subheader("End of document check (last 20 lines)")
            last_lines = "\n".join(text.splitlines()[-20:])
            st.text_area("End preview", last_lines, height=250)

            # ✅ 4) Save extracted text to a .txt file so you can open it and confirm
            text_path = save_path + ".txt"
            with open(text_path, "w", encoding="utf-8") as f:
                f.write(text)
            st.caption(f"Saved extracted text to: {text_path}")

            # ✅ 5) Keyword check (optional but useful)
            keywords = ["Sriaan", "Skills", "Projects"]
            found = {k: (k.lower() in text.lower()) for k in keywords}
            st.write("Keyword check:", found)

        except Exception as e:
            st.error(f"Could not extract text: {e}")
        

with tab_add_app:
    st.subheader("Add a job application")

    company = st.text_input("Company", placeholder="e.g., Salesforce")
    role = st.text_input("Role", placeholder="e.g., Associate Product Manager")
    date_applied = st.date_input("Date applied")
    status = st.selectbox("Status", ["applied", "interview", "rejected", "offer"])

    resumes = list_resumes()  # rows: (id, filename, file_path, uploaded_at)

    if len(resumes) == 0:
        st.warning("No resumes found yet. Upload a resume in the Upload tab first.")
    else:
        resume_options = {f"{r[1]} (id: {r[0]})": r[0] for r in resumes}
        chosen_label = st.selectbox("Resume used", list(resume_options.keys()))
        chosen_resume_id = resume_options[chosen_label]

        if st.button("Save application"):
            job_id = add_job(company, role, str(date_applied), status)
            app_id = add_application(job_id, chosen_resume_id)
            st.success(f"Saved! job_id={job_id}, application_id={app_id}")

with tab_history:
    st.subheader("Find the resume used for a job")

    lookup_company = st.text_input("Company to look up", placeholder="e.g., Salesforce")
    lookup_role = st.text_input("Role to look up", placeholder="e.g., Associate Product Manager")

    if st.button("Find resume"):
        result = get_resume_for_job(lookup_company, lookup_role)

        if not result:
            st.warning("No match found. Check spelling (company/role) or add the job first.")
        else:
            filename, file_path = result
            st.success(f"Resume found: {filename}")
        # Download button
            with open(file_path, "rb") as f:
                st.download_button(
                    label="Download this resume",
                    data=f,
                    file_name=filename,
                    mime="application/pdf" if filename.lower().endswith(".pdf") else "application/octet-stream",
                    )

        # Optional: show path for debugging
            st.caption(f"Stored at: {file_path}")

    
    st.subheader("Application history")

    rows = list_jobs()
    if not rows:
        st.info("No jobs saved yet.")
    else:
        for job in rows:
            job_id, company, role, date_applied, status, created_at = job
            st.write(f"**{company} — {role}** | {status} | applied: {date_applied} | job_id: {job_id}")

with tab_chat:
    st.subheader("Chatbot (Resume lookup)")

    st.write("Ask like: **What resume did I use for Salesforce Associate Product Manager**")
    st.write("Tip: You can also use: **for Salesforce - Associate Product Manager**")

    user_msg = st.text_input("Your question", placeholder="What resume did I use for Salesforce Associate Product Manager?")

    if st.button("Ask"):
        company, role = parse_company_role(user_msg)

        if not company or not role:
            st.warning("I couldn't understand that. Try: `for <Company> - <Role>`")
        else:
            result = get_resume_for_job(company, role)

            if not result:
                st.warning(f"No match found for company='{company}' and role='{role}'.")
            else:
                filename, file_path = result
                st.success(f"You used: {filename}")

                with open(file_path, "rb") as f:
                    st.download_button(
                        label="Download that resume",
                        data=f,
                        file_name=filename,
                        mime="application/pdf" if filename.lower().endswith(".pdf") else "application/octet-stream",
                    )
