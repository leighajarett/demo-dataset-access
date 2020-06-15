'''
This Cloud function is responsible for:
- Validating Requests 
- Creating Scratch Schema Dataset in BQ
- Creating a service account with temporary 
- Share JSON key with the SE
'''

import google.auth
from google.cloud import bigquery

credentials, project = google.auth.default()
dataset = 'trials-scratch'

def form_trigger(request):
    payload = request.get_json(silent=True)
    print("Payload was:", payload)
    return "OK"