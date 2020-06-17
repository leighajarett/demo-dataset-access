'''
This Cloud function is responsible for:
- Validating Requests 
- Creating Scratch Schema Dataset in BQ
- Creating a service account with temporary 
- Share JSON key with the SE
'''

import google.auth
from google.cloud import bigquery
from google.cloud import error_reporting
from google.oauth2 import service_account
import googleapiclient.discovery
import datetime
from google.cloud import secretmanager
import json

#authenticate into SDK
credentials, project = google.auth.default()
bq_client = bigquery.Client()
error_client = error_reporting.Client()

def form_trigger(request):   
    '''
    Handles the response from google forms
    '''
    request_json = request.get_json(silent=True)
    weeks = -1

    #check for email
    if request_json and 'email' in request_json:
        email = request_json['email'] 
    else:
        raise RuntimeError('No Email')

    #check for type (e.g. Internal, Customer / Prospect, Partner)
    if request_json and 'type' in request_json:
        request_type = request_json['type']
    else:
        raise RuntimeError('No Type')
    
    #check for name of request
    if request_json and 'name' in request_json:
        name = request_json['name']
    else:
        name = email[0:email.find('@')]
    name = name.lower()
    

    #check for weeks
    if request_json and 'weeks' in request_json:
        weeks = request_json['weeks']
    
    if 'Customer' in request_type:
        schema_name = 'trial_'+name+'_scratch'
        name = 'trial-'+name
    else:
        schema_name = name+'_scratch'

    #construct  Dataset object to send to the API
    dataset_id = "{}.{}".format(project, schema_name)
    dataset = bigquery.Dataset(dataset_id)
    dataset.location = "US"

    if not check_dataset(schema_name):
        #if the dataset does not exist try to create it
        try:
            dataset = bq_client.create_dataset(schema_name)  #make API request
            print('Finished making dataset: ', schema_name)
        except:
            raise RuntimeError('Issue creating dataset ' + schema_name)
    

    secret_link = ''
    service_email = name+'@sandbox-trials.iam.gserviceaccount.com'

    #create a service account
    if not check_service_account(name):
        create_service_account(name, request_type)
        print('Finished creating SA: ', name)
    
    #creates a new cloud secret with key if one does not exist
    secret_link = create_key(service_email, name, email, request_type)

    #update permissions with an expiration date  
    if weeks > 0:
        expiration = update_policy(name+'@sandbox-trials.iam.gserviceaccount.com', weeks)
    else:
        expiration = update_policy(name+'@sandbox-trials.iam.gserviceaccount.com')

    
    #return informaiton to be sent in an email
    return dataset_id, service_email, expiration, secret_link


def check_dataset(dataset):
    '''
    Checks to see if the scratch dataset exists
    '''

    datasets = list(bq_client.list_datasets())
    for dt in datasets:
        if dt.dataset_id == dataset:
            print('Dataset already exists')
            return True
    return False


def check_service_account(name):
    '''
    Checks to see if the service account already exists
    '''

    service = googleapiclient.discovery.build(
        'iam', 'v1', credentials=credentials)

    service_accounts = service.projects().serviceAccounts().list(
        name='projects/' + project).execute()

    for sa in service_accounts["accounts"]:
        if (name + '@sandbox-trials.iam.gserviceaccount.com') == sa["email"]:
            print('SA already exists')
            return True
    
    return False
    

def create_service_account(name, request_type):
    '''
    Creates a new service account
    '''

    user_string = name
    if 'Customer' in request_type:
        user_string = 'Opportunity ' + user_string

    description = 'This service account is for {} use,  for {}'.format(request_type, user_string)

    service = googleapiclient.discovery.build(
        'iam', 'v1', credentials=credentials)

    try:
        new_service_account = service.projects().serviceAccounts().create(
            name='projects/' + project,
            body={
                'accountId': name,
                'serviceAccount': {
                    'displayName' : name,
                    'description' : description
                }
            }).execute()
    
    except:
        raise RuntimeError("Issue creating service account " + name)
    
    return
     

def update_policy(member, weeks = None, role = 'trialuser', is_new = True):
    '''
    Updates IAM policy to add members to a role with an expiration condition
    '''

    role_name = 'projects/{}/roles/{}'.format(project,role)
    member_string = 'serviceAccount:'+ member

    service = googleapiclient.discovery.build(
        "cloudresourcemanager", "v1", credentials=credentials
        )

    policy = (
        service.projects()
        .getIamPolicy(
            resource=project,
            body={"options": {"requestedPolicyVersion": 3}}
        )
        .execute()
        )

    #if this is an existing service account, try to find its binding and remove it
    if not is_new :
        for bind in policy["bindings"]:
            if bind["role"] == role_name and member_string in bind["members"]:
                #remove it from the binding
                bind['members'].pop(member_string)
                print('Removed {} from {} binding'.format(member, role_name))
            
    #now create a new binding with the expiration time and add to policy
    new_binding = {
        'role': role_name,
        'members': [member_string]
        }

    if weeks is not None:
        new_binding['condition'] = {}
        expiration_time = datetime.datetime.now() + datetime.timedelta(weeks=weeks)
        new_binding['condition']['expression'] = 'request.time < timestamp("{}Z")'.format(expiration_time.isoformat())
        new_binding['condition']['title'] = 'Expiration'
        
    policy["bindings"].append(new_binding)

    policy = (
        service.projects()
        .setIamPolicy(resource=project, body={"policy": policy})
        .execute()
        )

    print('Updated policy with new binding: ', new_binding)

    if weeks is not None:
        return expiration_time

    else:
        return 'Never'


def create_key(service_account_email, name, email, request_type):
    '''
    This function:
        -Creates a key for a service account
        -Adds it to a secret
        -Shares the secret with an email and return the link to view the secret
    '''

    service = googleapiclient.discovery.build(
        'iam', 'v1', credentials=credentials)

    key = service.projects().serviceAccounts().keys().create(
        name='projects/-/serviceAccounts/' + service_account_email, body={}
        ).execute()

    secret_client = secretmanager.SecretManagerServiceClient()
    parent = secret_client.project_path(project)

    secret_id = name
    secret_exists = False
    secret_path = secret_client.secret_path(project, secret_id)

    for secret in secret_client.list_secrets(parent):
        if secret_id == secret.name.split('/secrets/')[1]:
            secret_exists = True 
            print('Secret already exists')

    if not secret_exists:
        response = secret_client.create_secret(parent, secret_id, {
            'replication': {
                'automatic': {},
                }
            }
        )
        response = secret_client.add_secret_version(secret_path, {'data': json.dumps(key).encode('UTF-8')})
        print('Created new secret')

    secret_policy = {'version': 3, 'bindings': [
        {'role': 'roles/secretmanager.secretAccessor', 'members': ['user:'+email]},
        {'role': 'roles/secretmanager.viewer', 'members': ['user:'+email]}
        ]}
    secret_client.set_iam_policy(secret_path, secret_policy)
    print('Set new IAM policy for secret')
    
    return 'https://console.cloud.google.com/security/secret-manager/secret/{}?project={}'.format(secret_id,project)

