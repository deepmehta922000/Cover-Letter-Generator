import streamlit as st
from langchain_community.document_loaders import WebBaseLoader
from chains import Chain
from portfolio import Portfolio
from utils import clean_text
from PyPDF2 import PdfReader
import io
import fitz


def load_resume(uploaded_file):
    """Extracts text from uploaded PDF or text resume."""
    if uploaded_file.type == "application/pdf":
        # Extract text using PyMuPDF
        pdf_text = ""
        with fitz.open(stream=uploaded_file.read(), filetype="pdf") as pdf_doc:
            for page in pdf_doc:
                pdf_text += page.get_text()
        return pdf_text
    else:
        # Assume it's a plain text file
        return str(uploaded_file.read(), "utf-8")


def create_streamlit_app(llm, portfolio, clean_text):
    # Page Navigation
    page = st.sidebar.radio("Navigation", ["Upload Resume", "Generate Cover Letter"])

    # Page 1: Upload Resume
    if page == "Upload Resume":
        st.title("Step 1: Upload or Paste Your Resume")
        st.write("Upload your resume as a PDF or text file, or paste your resume text here.")

        # Tabs for uploading or pasting resume content
        resume_tabs = st.tabs(["📄 Upload Resume", "✍️ Paste Resume Text"])
        with resume_tabs[0]:
            uploaded_resume = st.file_uploader("Upload your resume (PDF or Text)", type=["pdf", "txt"])
            if uploaded_resume:
                resume_content = load_resume(uploaded_resume)
                st.session_state["resume_content"] = resume_content
                st.success("Resume uploaded successfully.")
        with resume_tabs[1]:
            pasted_resume = st.text_area("Or, paste your resume text here")
            if pasted_resume:
                st.session_state["resume_content"] = pasted_resume
                st.success("Resume text saved successfully.")

            

    # Page 2: Generate Cover Letter
    elif page == "Generate Cover Letter":
        st.title("Cover Letter Generator")

        # Ensure resume has been uploaded or pasted
        if "resume_uploaded" not in st.session_state or not st.session_state["resume_uploaded"]:
            st.warning("Please upload or paste your resume on the 'Upload Resume' page before proceeding.")
            st.stop()

        # Step 2: Job Description Input
        st.header("Step 2: Input Job Description")
        st.write("Provide the job description by pasting the job URL or the job details directly.")

        # Tabs for job description input
        job_tabs = st.tabs(["🔗 Enter Job Posting URL", "📝 Paste Job Description"])
        with job_tabs[0]:
            url_input = st.text_input("Enter the URL to the job posting:")
        with job_tabs[1]:
            job_description = st.text_area("Or, paste the job description here")

        # Step 3: Additional Customizations
        st.header("Step 3: Add Additional Information")
        st.write("Optional: Enter specific information you’d like highlighted in your cover letter and select a cover letter format.")

        # Input for additional information and format choice
        additional_info = st.text_area("Additional information to include (e.g., relevant skills, achievements)")
        format_options = st.selectbox(
            "Preferred cover letter format",
            ["Professional", "Conversational", "Concise", "Detailed"]
        )

        # Step 4: Generate Cover Letter or Review Resume
        st.header("Step 4: Generate Cover Letter or Review Resume")
        st.write("Once you have completed the steps, choose either to review your resume for skill matching or to generate your cover letter.")

        # Action buttons
        review_button = st.button("Review Resume for Skill Match")
        generate_button = st.button("Generate Cover Letter")

        # Cover Letter Generation Logic
        if generate_button:
            try:
                # Use job description from URL or pasted text
                if url_input:
                    loader = WebBaseLoader([url_input])
                    data = clean_text(loader.load().pop().page_content)
                elif job_description:
                    data = clean_text(job_description)
                else:
                    st.error("Please enter a job URL or paste a job description.")
                    return

                portfolio.load_portfolio()
                jobs = llm.extract_jobs(data)
                for job in jobs:
                    skills = job.get('skills', [])
                    links = portfolio.query_links(skills)
                    
                    # Use additional info and format choice in cover letter generation
                    email = llm.write_mail(
                        job,
                        links,
                        resume_text=st.session_state["resume_content"],
                        additional_info=additional_info,
                        format_choice=format_options
                    )

                    # Display the cover letter
                    formatted_email = email.replace("\n", "  \n")
                    st.markdown(formatted_email, unsafe_allow_html=True)

            except Exception as e:
                st.error(f"An error occurred: {e}")

        # Resume Review Logic
        if review_button:
            try:
                # Load job description and extract required skills
                if url_input:
                    loader = WebBaseLoader([url_input])
                    data = clean_text(loader.load().pop().page_content)
                elif job_description:
                    data = clean_text(job_description)
                else:
                    st.error("Please enter a job URL or paste a job description.")
                    return

                jobs = llm.extract_jobs(data)
                if jobs:
                    job_skills = jobs[0].get('skills', [])
                    resume_skills = llm.extract_skills_from_resume(st.session_state["resume_content"])
                    review = llm.review_resume(job_skills, resume_skills)

                    # Display review results
                    st.write("### Resume Review")
                    st.write(f"**Skill Match Percentage:** {review['match_percentage']:.1f}%")
                    st.write(review["feedback"])
                    if review["missing_skills"]:
                        st.write("**Missing Skills:**")
                        st.write(", ".join(review["missing_skills"]))
                else:
                    st.error("Could not extract job details. Please check the job URL.")

            except Exception as e:
                st.error(f"An error occurred: {e}")





if __name__ == "__main__":
    chain = Chain()
    portfolio = Portfolio()
    st.set_page_config(layout="wide", page_title="Cover Letter Generator", page_icon="📧")
    create_streamlit_app(chain, portfolio, clean_text)
