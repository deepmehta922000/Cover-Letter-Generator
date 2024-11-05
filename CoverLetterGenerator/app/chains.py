import os
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.exceptions import OutputParserException
from dotenv import load_dotenv
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

load_dotenv()
inch = 2

class Chain:
    def __init__(self):
        self.llm = ChatGroq(temperature=0, groq_api_key=os.getenv("GROQ_API_KEY"), model_name="llama-3.1-70b-versatile")

    def extract_jobs(self, cleaned_text):
        prompt_extract = PromptTemplate.from_template(
            """
            ### SCRAPED TEXT FROM WEBSITE:
            {page_data}
            ### INSTRUCTION:
            The scraped text is from the career's page of a website.
            Your job is to extract the job postings and return them in JSON format containing the following keys: `role`, `experience`, `skills` and `description`.
            Only return the valid JSON.
            ### VALID JSON (NO PREAMBLE):
            """
        )
        chain_extract = prompt_extract | self.llm
        res = chain_extract.invoke(input={"page_data": cleaned_text})
        try:
            json_parser = JsonOutputParser()
            res = json_parser.parse(res.content)
        except OutputParserException:
            raise OutputParserException("Context too big. Unable to parse jobs.")
        return res if isinstance(res, list) else [res]

    def write_mail(self, job, links, resume_text, additional_info=None, format_choice=None):
        prompt_email = PromptTemplate.from_template(
            """
            ### JOB DESCRIPTION:
            {job_description}

            ### RESUME:
            {resume_text}

            ### INSTRUCTION:
            You are Deep Mehta, a Data Scientist. Your job is to write a {format_choice} cover letter to the Hiring Manager regarding the job 
            described above, explaining how Deep Mehta's skills and experience (from the resume) align with the role.
            Don't copy paste from the resume, only add what is relevant. Keep it short and sweet.
            Do not provide a preamble.

            ### ADDITIONAL Information:
            {additional_info}

            ### EMAIL (NO PREAMBLE):
            """
        )
        chain_email = prompt_email | self.llm
        
        # Include the additional_info and format_choice in the invocation
        res = chain_email.invoke({
            "job_description": str(job),
            "resume_text": resume_text,
            "link_list": links,
            "additional_info": additional_info,  # Added this line
            "format_choice": format_choice        # Added this line
        })
    
        return res.content

  
    
    def generate_pdf(self, cover_letter_text, filename="cover_letter.pdf"):
        pdf_path = f"Outputs\{filename}"  # Use a temp directory for Streamlit compatibility
        c = canvas.Canvas(pdf_path, pagesize=letter)
        width, height = letter
        
        # Margins and text settings
        margin = inch  # 1-inch margin
        text_width = width - 2 * margin
        line_height = 14  # Space between lines

        # Header (Sender’s Information, Date)
        sender_info = "Deep Mehta\nRochester, NY\nEmail: deep.mehta@example.com\nPhone: (555) 555-5555"
        date = "November 1, 2024"
        self.add_text_block(c, sender_info, margin, height - inch, text_width, "Helvetica-Bold", 12)
        self.add_text_block(c, date, margin, height - 1.5 * inch, text_width, "Helvetica", 12)

        # Add some space before the main content
        body_start_y = height - 2 * inch

        # Main Body (Cover Letter Content with Wrapping)
        formatted_content = self.wrap_text(cover_letter_text, c, text_width)
        self.add_text_block(c, formatted_content, margin, body_start_y, text_width, "Helvetica", 12, line_height)

        # Signature
        signature_text = "\nSincerely,\n\nDeep Mehta"
        self.add_text_block(c, signature_text, margin, body_start_y - 4 * inch, text_width, "Helvetica", 12)

        # Finalize and save
        c.showPage()
        c.save()
        return pdf_path

    def wrap_text(self, text, canvas, width):
        """Helper function to wrap text to fit within a specified width."""
        words = text.split()
        lines = []
        current_line = ""
        for word in words:
            test_line = f"{current_line} {word}".strip()
            if canvas.stringWidth(test_line, "Helvetica", 12) <= width:
                current_line = test_line
            else:
                lines.append(current_line)
                current_line = word
        if current_line:
            lines.append(current_line)
        return "\n".join(lines)  # Return joined lines as a single string for consistent formatting

    def add_text_block(self, canvas, text, x, y, max_width, font_name, font_size, line_height=14):
        """Draws text on the canvas with specified formatting and wrapping."""
        lines = text.splitlines()
        text_obj = canvas.beginText(x, y)
        text_obj.setFont(font_name, font_size)
        text_obj.setLeading(line_height)
        for line in lines:
            text_obj.textLine(line)
        canvas.drawText(text_obj)

    def extract_skills_from_resume(self, resume_text):
        prompt_extract_skills = PromptTemplate.from_template(
            """
            ### RESUME TEXT:
            {resume_text}

            ### INSTRUCTION:
            Identify and extract all relevant technical and professional skills mentioned in the resume text.
            Focus on specific skills, technologies, programming languages, frameworks, tools, and domain knowledge.
            Return the skills as a list, without general terms (e.g., "teamwork," "communication") and avoid job titles or company names.
            """
        )
        chain_extract_skills = prompt_extract_skills | self.llm
        res = chain_extract_skills.invoke(input={"resume_text": resume_text})
        return res.content.strip().split(", ")


    def review_resume(self, job_skills, resume_skills):
        """Calculates match percentage and identifies missing skills."""
        # Find intersection of skills and calculate match percentage
        matched_skills = set(job_skills).intersection(resume_skills)
        missing_skills = set(job_skills) - matched_skills

        match_percentage = (len(matched_skills) / len(job_skills)) * 100 if job_skills else 0
        feedback = f"Your resume matches {match_percentage:.1f}% of the required skills."

        if missing_skills:
            feedback += "\n\nConsider adding these missing skills:\n" + ", ".join(missing_skills)
        else:
            feedback += "\n\nGreat job! Your resume includes all required skills."

        return {
            "match_percentage": match_percentage,
            "feedback": feedback,
            "missing_skills": list(missing_skills)
        }

    
    def match_skills(self, resume_text, required_skills):
        prompt_skill_match = PromptTemplate.from_template(
            """
            ### RESUME TEXT:
            {resume_text}

            ### REQUIRED SKILLS:
            {required_skills}

            ### INSTRUCTION:
            Compare the skills listed in the resume with the required skills above.
            Provide an honest review of the skills match, including:
            - A percentage match of skills possessed versus required
            - A list of skills from the required list that are missing in the resume
            Format the response clearly, providing the match percentage and missing skills.
            """
        )
        chain_skill_match = prompt_skill_match | self.llm
        res = chain_skill_match.invoke(input={"resume_text": resume_text, "required_skills": required_skills})
        return res.content.strip() 

if __name__ == "__main__":
    print(os.getenv("GROQ_API_KEY"))