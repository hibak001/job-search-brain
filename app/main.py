import streamlit as st
import os

st.set_page_config(page_title="Job Search Brain", layout="wide")
st.title("Job Search Brain 🤖")

st.subheader("Upload documents")

doc_type = st.selectbox(
    "What are you uploading?",
    ["Resume", "Job Description", "Cover Letter", "Notes"]
)

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

