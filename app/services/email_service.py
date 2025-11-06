from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib
from langchain import LLMChain, PromptTemplate
from langchain.llms import OpenAI

class EmailService:
    def __init__(self, smtp_server, smtp_port, sender_email, password):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.sender_email = sender_email
        self.password = password
        self.llm = OpenAI(temperature=0.7)

    def generate_email_content(self, candidate_name, position, interview_time):
        template = """
        Write a professional and warm email to schedule an interview with {candidate_name} 
        for the {position} position at {interview_time}.
        The email should be:
        1. Professional but friendly
        2. Clear about the interview details
        3. Encouraging and positive
        """
        
        prompt = PromptTemplate(
            input_variables=["candidate_name", "position", "interview_time"],
            template=template
        )
        
        chain = LLMChain(llm=self.llm, prompt=prompt)
        return chain.run(candidate_name=candidate_name, 
                        position=position, 
                        interview_time=interview_time)

    def send_interview_invite(self, to_email, candidate_name, position, interview_time):
        msg = MIMEMultipart()
        msg['From'] = self.sender_email
        msg['To'] = to_email
        msg['Subject'] = f"Interview Invitation - {position}"

        body = self.generate_email_content(candidate_name, position, interview_time)
        msg.attach(MIMEText(body, 'plain'))

        with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
            server.starttls()
            server.login(self.sender_email, self.password)
            server.send_message(msg)