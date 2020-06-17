# demo-dataset-access
Cloud function, for granting temporary credentials / scratch schema for connecting to a Looker Instance. For use in an internal Google Apps Script that is triggered by a Form submission witht the necessary information. An email is then sent to the submitter with details on how to to setup the connection.

1. Validate the request 
2. Creates a Service Account if one for that request does not already exist
3. Creates a Scratch Dataset if one for that request does not already exist
4. Update the policy for the service account so that it has the trialuser role for the number of weeks specified in the request
5. Create a Cloud Secret with the JSON key for the Serice Account
6. Update the policy for the secret so that the submitter has view capabilities
7. Return the scratch dataset name, the SA email, the date the permissions expire, and a link to view the secret in Google Cloud Coneole
