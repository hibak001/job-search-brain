import streamlit as st
import os
import re

from core.extract_text import extract_text
from core.db import (
    init_db,
    add_document,
    list_resumes,
    add_job,
    add_application,
    list_jobs,
    get_resume_for_job,
    list_documents,
    list_jobs_by_company,
    list_jobs_for_resume,
)



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



def detect_intent(msg: str) -> str:
    m = msg.lower().strip()

    if "list resumes" in m or "show resumes" in m or "my resumes" in m:
        return "LIST_RESUMES"

    if "list jobs" in m and " at " in m:
        return "LIST_JOBS_BY_COMPANY"

    if "what resume did i use" in m or "which resume did i use" in m:
        return "RESUME_FOR_JOB"

    if "jobs did i use" in m and "resume" in m:
        return "JOBS_FOR_RESUME"

    return "UNKNOWN"


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
    if "chat" not in st.session_state:
        st.session_state.chat = []  # list of {"role": "user"/"bot", "content": str}

    st.subheader("Chatbot (Resume lookup)")

    st.write("Ask like: **What resume did I use for Salesforce Associate Product Manager**")
    st.write("Tip: You can also use: **for Salesforce - Associate Product Manager**")

    for m in st.session_state.chat:
        if m["role"] == "user":
            st.markdown(f"**You:** {m['content']}")
        else:
            st.markdown(f"**Bot:** {m['content']}")

        # --- Download button area (Chatbot tab) ---
    if "last_resume_found" not in st.session_state:
        st.session_state.last_resume_found = None

    if st.session_state.last_resume_found:
        fp = st.session_state.last_resume_found["file_path"]
        fn = st.session_state.last_resume_found["filename"]

        st.info("Download the resume I found:")
        with open(fp, "rb") as f:
            st.download_button(
                label=f"Download {fn}",
                data=f,
                file_name=fn,
                mime="application/pdf" if fn.lower().endswith(".pdf") else "application/octet-stream",
            )


    st.divider()

    user_msg = st.text_input("Type a message", placeholder="Try: list resumes")

    if st.button("Send"):
        if not user_msg.strip():
            st.warning("Type something first.")
        else:
            # Save user message
            st.session_state.chat.append({"role": "user", "content": user_msg})

            intent = detect_intent(user_msg)

            # 1) List resumes
            if intent == "LIST_RESUMES":
                resumes = list_resumes()
                if not resumes:
                    bot = "You have no resumes uploaded yet."
                else:
                    lines = ["Here are your uploaded resumes:"]
                    for r in resumes:
                        rid, filename, path, uploaded_at = r
                        lines.append(f"- {filename} (id: {rid})")
                    bot = "\n".join(lines)

            # 2) List jobs by company: "list jobs at Salesforce"
            elif intent == "LIST_JOBS_BY_COMPANY":
                company = user_msg.lower().split(" at ", 1)[1].strip()
                jobs = list_jobs_by_company(company)
                if not jobs:
                    bot = f"No jobs found for company: {company}"
                else:
                    lines = [f"Jobs at {company}:"]
                    for j in jobs:
                        jid, comp, role, date_applied, status, created_at = j
                        lines.append(f"- {role} | {status} | applied: {date_applied}")
                    bot = "\n".join(lines)

            # 3) Resume used for a job
            elif intent == "RESUME_FOR_JOB":
                company, role = parse_company_role(user_msg)

                if not company or not role:
                    bot = "Try: `what resume did i use for Salesforce - Associate Product Manager`"
                    st.session_state.last_resume_found = None   # ✅ clear

                else:
                    res = get_resume_for_job(company, role)

                    if not res:
                        bot = f"No resume found for {company} / {role}."
                        st.session_state.last_resume_found = None   # ✅ clear

                    else:
                        filename, file_path = res
                        bot = f"You used: {filename}"

                        # ✅ save for download button rendering
                        st.session_state.last_resume_found = {
                            "filename": filename,
                            "file_path": file_path
                        }

             

            # 4) Jobs for a resume id: "what jobs did i use resume 1 for"
            elif intent == "JOBS_FOR_RESUME":
                m = re.search(r"resume\s+(\d+)", user_msg.lower())
                if not m:
                    bot = "Try: `what jobs did I use resume 1 for`"
                else:
                    resume_id = int(m.group(1))
                    jobs = list_jobs_for_resume(resume_id)
                    if not jobs:
                        bot = f"No jobs found for resume id {resume_id}."
                    else:
                        lines = [f"Jobs that used resume id {resume_id}:"]
                        for j in jobs:
                            jid, comp, role, date_applied, status = j
                            lines.append(f"- {comp} — {role} | {status} | applied: {date_applied}")
                        bot = "\n".join(lines)

            else:
                bot = (
                    "I can help with:\n"
                    "- `list resumes`\n"
                    "- `list jobs at <company>`\n"
                    "- `what resume did I use for <company> - <role>`\n"
                    "- `what jobs did I use resume <id> for`"
                )

            # Save bot message
            st.session_state.chat.append({"role": "bot", "content": bot})

            # Re-render with new messages visible
            st.rerun()

