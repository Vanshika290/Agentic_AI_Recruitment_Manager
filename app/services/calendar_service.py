from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import os
import sys

# Enable non-HTTPS for local testing
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

SCOPES = ['https://www.googleapis.com/auth/calendar.events']
TOKEN_PATH = "token.json"
CREDENTIALS_PATH = "credentials.json"

class CalendarService:
    def __init__(self):
        self.creds = None
        self.service = None
        print("Starting Calendar Service setup...")
        self.setup_credentials()

    def setup_credentials(self):
        try:
            if os.path.exists(TOKEN_PATH):
                print("Loading existing token...")
                self.creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
            
            if not self.creds or not self.creds.valid:
                print("Starting new OAuth flow...")
                flow = InstalledAppFlow.from_client_secrets_file(
                    CREDENTIALS_PATH, 
                    SCOPES
                )
                self.creds = flow.run_local_server(port=0)
                
                print("Saving new token...")
                with open(TOKEN_PATH, 'w') as token:
                    token.write(self.creds.to_json())

            self.service = build('calendar', 'v3', credentials=self.creds)
            print("Calendar Service initialized successfully!")
            return True
        except Exception as e:
            print(f"Setup error: {str(e)}")
            return False

    def test_calendar(self):
        """Test calendar access"""
        try:
            now = datetime.utcnow().isoformat() + 'Z'
            events_result = self.service.events().list(
                calendarId='primary', 
                timeMin=now,
                maxResults=1,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            print("Successfully accessed calendar!")
            return True
        except Exception as e:
            print(f"Calendar test failed: {str(e)}")
            return False
    def schedule_interview(self, candidate_email, recruiter_email, interview_time, duration=60):
        """Schedule an interview and send calendar invites"""
        try:
            event = {
                'summary': 'Technical Interview',
                'description': 'Interview session for technical assessment',
                'start': {
                    'dateTime': interview_time.isoformat(),
                    'timeZone': 'UTC',
                },
                'end': {
                    'dateTime': (interview_time + timedelta(minutes=duration)).isoformat(),
                    'timeZone': 'UTC',
                },
                'attendees': [
                    {'email': candidate_email},
                    {'email': recruiter_email},
                ],
                'reminders': {
                    'useDefault': True,
                },
            }
            
            event = self.service.events().insert(
                calendarId='primary',
                sendNotifications=True,
                body=event
            ).execute()
            
            print(f"Interview scheduled successfully! Event ID: {event.get('id')}")
            return event
        except Exception as e:
            print(f"Failed to schedule interview: {str(e)}")
            return None

    def list_upcoming_interviews(self, max_results=10):
        """List upcoming interview events"""
        try:
            now = datetime.utcnow().isoformat() + 'Z'
            events_result = self.service.events().list(
                calendarId='primary',
                timeMin=now,
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            return events_result.get('items', [])
        except Exception as e:
            print(f"Failed to fetch upcoming interviews: {str(e)}")
            return []

# Test the new functionality
if __name__ == "__main__":
    calendar = CalendarService()
    
    # Test scheduling an interview
    interview_time = datetime.now() + timedelta(days=1)
    test_event = calendar.schedule_interview(
        "candidate@example.com",
        "recruiter@example.com",
        interview_time
    )
    
    if test_event:
        print("\nUpcoming interviews:")
        upcoming = calendar.list_upcoming_interviews(3)
        for event in upcoming:
            start = event['start'].get('dateTime', event['start'].get('date'))
            print(f"- {event['summary']} at {start}")

if __name__ == "__main__":
    calendar = CalendarService()
    calendar.test_calendar()