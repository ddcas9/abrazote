# abrazote

This is a basic e-consents API. Simple CRUD functionality is supported. 

For the app to work in development, you'll need to specify the following environment variables:

```
# in case you need one: 
SECRET_KEY
#your database connection string, note that you need to specify the driver for SQLALCHEMY, e.g. postgresql+psycopg2, not just postgresql. 
SQLALCHEMY_DATABASE_URI
# This should actually be called "BASE_URL", feel free to submit a PR for that! You must set it to whatever the current environment's base url is. If you use Heroku, set it in the environment dashboard to the production base url. 
PROD_BASE_URL="http://localhost:5000"
# In case you need the azure language service, not needed for this current version:
AZURE_LANGUAGE_KEY
AZURE_LANGUAGE_ENDPOINT

# Your api key and location for azure translator:
AZURE_TRANSLATOR_KEY
AZURE_TRANSLATOR_LOCATION
# You can set the app mode to DEV to add a / to the base url. Render adds a slash automatically.
APP_MODE=PROD
# Sets the languages that you will use to automatically translate a consent form data object upon its being received.
SUPPORTED_LANGUAGES_STR=["en", "es", "fr"]

```


Here's an example request body for creating an e-consent (you don't need a Consent Type header, but include one just in case. Send this to the route http://<your_ip>:5000/consents as a post request.  

```
{
    "sections": [
        {
            "title": "Section One",
            "content": "We collect certain data from you to meet mandatory requirements regarding medical notes. There is a legal requirement to keep medical notes for a period of time after treatment. This can vary in length depending on your age and ability to consent but will be for a minimum of 7 years. Your details will be destroyed after this period."
        },
        {
            "title": "Section Two",
            "content": "We also collect data to assist in the administration of our businesses to provide you with an effective service. We would like to use your contact details to assist with the administration of your appointments/changes to scheduled appointments and/or reminders about appointments. To further enhance our service to you, we would like to be able to update you on any information regarding the practice."
        },
        {
            "title": "Section Three",
            "content": "We take your privacy seriously and will take all reasonable steps to ensure the protection if your data. Please note that your right to be forgotten cannot override the legal requirements to keep medical notes for the mandatory periods. You can request a copy of any data held about you by submitting an Access Request."
        }
    ]

}
```

An e-consent of this size will work in development, but not in the production application because the inserts are performed as a batch. In a later version, the backend will make the inserts individually. 

Notable other routes:


http://<your_ip>:5000/consents/<consent_id>/sections  - to check what sections are included in a given consent and to identify the section id of the section you want to translate

http://<your_ip>:5000/sections/<section_id> - Get an individual section or update it (put request instead of get). If you're updating, the old translations will be soft deleted and new translations will be generated. 

http://<your_ip>:5000/<consent_id>/<lang> - this gets a consent translated into the target language lang passed in as a query parameter. The SUPPORTED_LANGUAGES_STR environment variable should be set to Spanish (es) and French (fr), but feel free to try others. The form of the string is "["es", "fr"]". Try not to deploy more than two languages, since these are what the consents are instantly translated to upon submission for now. If lang is not in SUPPORTED_LANGUAGES, the translate route will be called with the target lang (e.g. 'ja' or 'it'). 



