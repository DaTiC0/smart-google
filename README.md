# Smart-Google

Google Home integration to your custom devices by Google action and Python whit Flask Framework

## Environment

Using Heroku to deploy python application

Using Firebase for database

*Export this variables*

- SECRET_KEY
- SQLALCHEMY_DATABASE_URI
- MQTT_BROKER_URL
- MQTT_USERNAME
- MQTT_PASSWORD
- API_KEY
- AGENT_USER_ID
- SERVICE_ACCOUNT_FILE
- FIREBASE_ADMINSDK_FILE
- DATABASEURL
- PROJECT_ID
- PRIVATE_KEY_ID
- PRIVATE_KEY
- CLIENT_EMAIL
- CLIENT_X509_CERT_URL

### Google Service Account

You need to generate and download `service_account_file.json` from google cloud
extract from this file
'PROJECT_ID'
'PRIVATE_KEY_ID'
'PRIVATE_KEY'
'CLIENT_EMAIL'
'CLIENT_X509_CERT_URL'
and export to environment or save in .env file for security
generate_service_account_file.py file will genearate service account

### TESTING

Some Testing in VENV just for now. container env is coming ..
