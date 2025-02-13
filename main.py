from datetime import datetime, timedelta
import json
import requests
import os.path
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

class TruckersMPCalendarEvent():
    
    def __init__(self):
        self.int_events = []
        # Load configuration from config.json
        with open('config.json', 'r') as config_file:
            config = json.load(config_file)

        # Extract configuration values
        self.URL = config['url']
        self.SCOPES = config['scopes']
        self.CALENDAR_ID = config['calendar_id']
    
    def process_event(self, events):
        for event in events:
            for game in ['ETS2']:
                if game in event['game']:
                    interesting_event = {}
                    interesting_event['name'] = event['name'] + " " + event['event_type']['key']
                    interesting_event['description'] = (
                    f"Departure: {event['departure']['location']}, {event['departure']['city']}"
                    f"Arrival: {event['arrive']['location']}, {event['arrive']['city']} \n"
                    f"Game: {event['game']} \n"
                    f"Server: {event['server']['name']} - {event['server']['id']} \n"
                    f"Meetup At: {event['meetup_at']} \n"
                    f"Start At: {event['start_at']}"
                    )
                    interesting_event['start'] = event["meetup_at"]
                    self.int_events.append(interesting_event)
    
    def fetch_truckersmp_events(self):
        try:
            # Make an HTTP GET request to the TruckersMP events API
            response = requests.get(self.URL)
            # Check if the request was successful
            if response.status_code == 200:
                # Parse the JSON response
                data = response.json()
                for event_type in ['upcoming', 'now', 'today', 'featured']:
                    # Check if the API returned events data
                    if event_type in data['response']:
                        events = data['response'][event_type]
                        self.process_event(events)
                return self.int_events
            else:
                print(f"Failed to fetch events. Status code: {response.status_code}")
                return None
        except requests.exceptions.RequestException as e:
            print(f"An error occurred: {e}")
            return None
    
    def event_exists(self, service, event):
        start_dt = datetime.strptime(event['start'], "%Y-%m-%d %H:%M:%S")
        end_dt = start_dt + timedelta(hours=2)
        
        # Convert to RFC3339 format
        start_time = start_dt.isoformat() + "Z"
        end_time = end_dt.isoformat() + "Z"

        # Use the events.list method to search for events in the given time range
        events_result = service.events().list(
            calendarId=self.CALENDAR_ID,
            timeMin=start_time,
            timeMax=end_time,
            q=event['name'],
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        events = events_result.get('items', [])

        for existing_event in events:
            if existing_event['summary'] == event['name']:
                return True
        return False
    
    def add_event_to_google_calendar(self, service, event):
        event_start_str = event['start']

        # Convert to ISO 8601 format
        start_datetime = datetime.strptime(event_start_str, "%Y-%m-%d %H:%M:%S").isoformat() + "Z"
        end_datetime = datetime.strptime(event_start_str, "%Y-%m-%d %H:%M:%S") + timedelta(hours=2)
        end_datetime = end_datetime.isoformat() + "Z"

        event_body = {
            'summary': event['name'],
            'description': event['description'],
            'start': {
                'dateTime': start_datetime,
                'timeZone': 'UTC',  # Adjust if needed
            },
            'end': {
                'dateTime': end_datetime,  # Assuming events have a fixed duration, adjust accordingly
                'timeZone': 'UTC',  # Adjust if needed
            },
            'reminders': {
                'useDefault': False,  # Disable default reminders
                'overrides': []  # No custom reminders
            }
        }
        event_result = service.events().insert(calendarId=self.CALENDAR_ID, body=event_body).execute()
        print(f"Event created: {event_result.get('htmlLink')}")

    def authenticate_google_calendar(self):
        creds = None
        if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file('token.json', self.SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file('google_token.json', self.SCOPES)
                creds = flow.run_local_server(port=0)
            with open('token.json', 'w') as token:
                token.write(creds.to_json())
        service = build('calendar', 'v3', credentials=creds)
        return service

def main():
    # Fetch TruckersMP events
    # Example usage
    obj = TruckersMPCalendarEvent()
    events = obj.fetch_truckersmp_events()
    sorted_events = sorted(
    [e for e in events if e.get('start') is not None],
    key=lambda e: datetime.strptime(e['start'], "%Y-%m-%d %H:%M:%S")
    )
    if sorted_events:
        # Authenticate with Google Calendar
        service = obj.authenticate_google_calendar()
        i = 0
        # Add each event to Google Calendar
        for event in sorted_events:
            i+=1
            if not obj.event_exists(service, event):
                obj.add_event_to_google_calendar(service, event)     
            if i == 7:
                break   
    else:
        print("No events found.")

if __name__ == '__main__':
    main()
        
