from flask import Blueprint, jsonify, request
import requests, uuid, json
import os
from dotenv import load_dotenv
load_dotenv()

AZURE_KEY = 'AZURE_TRANSLATOR_KEY'
AZURE_LOCATION = 'AZURE_TRANSLATOR_LOCATION'
AZURE_TRANSLATOR_DETECT_ROUTE = '/detect'
AZURE_TRANSLATOR_TRANSLATE_ROUTE = '/translate'


# Add your subscription key and endpoint
subscription_key = os.environ.get(AZURE_KEY)
endpoint = 'https://api.cognitive.microsofttranslator.com'

# Add your location, also known as region. The default is global.
# This is required if using a Cognitive Services resource.
location = os.environ.get(AZURE_LOCATION)



def translation_api_request(path, body, src=None, targets=None, subscription_key = subscription_key, location=location, api_version='3.0'): 
    """
    Calls the azure translation API on the given body of text documents. 
    """
    constructed_url = endpoint + path
    params = {
        'api-version': api_version
    }
    if path == AZURE_TRANSLATOR_TRANSLATE_ROUTE: 
        if not targets: 
            raise Exception("Must have at least one target language if translating.")
        if src: 
            params['from'] = src
        params['to'] = targets


    headers = {
        'Ocp-Apim-Subscription-Key': subscription_key,
        'Ocp-Apim-Subscription-Region': location,
        'Content-type': 'application/json',
        'X-ClientTraceId': str(uuid.uuid4())
    }

    # You can pass more than one object in body.
    try:
        request_body = requests.post(constructed_url, params=params, headers=headers, json=body)
        response = request_body.json()
        return response
    except Exception as err:
        print("Encountered exception. {}".format(err))
    
    

from azure.ai.textanalytics import TextAnalyticsClient
from azure.core.credentials import AzureKeyCredential

# If you want to use cognitive services for detection uncomment below and substitute:  

'''
key = str(os.environ.get('AZURE_LANGUAGE_KEY'))
endpoint = os.environ.get('AZURE_LANGUAGE_ENDPOINT')
print(os)

# Authenticate the client using your key and endpoint 
def authenticate_client():
    ta_credential = AzureKeyCredential(key)
    text_analytics_client = TextAnalyticsClient(
            endpoint=endpoint, 
            credential=ta_credential)
    return text_analytics_client

client = authenticate_client()
try:
    documents = ["Ce document est rédigé en Français."]
    response = client.detect_language(documents = documents, country_hint = 'us')[0]

except Exception as err:
        print("Encountered exception. {}".format(err))
language_guess = {
        'language': response.primary_language.iso6391_name, 
        'confidence': response.primary_language.confidence_score, 
        'warnings': response.warnings,
        'is_error': response.is_error,
    }
'''


translator = Blueprint('translator', __name__)


@translator.route('/translate', methods=['POST'])
def translate():
    """
    This route uses the Azure Translator API and queries it in a similar fashion to the
    detect_language method. Note that we coerce any input into JSON. 
    
    The body must be a json of the form: 
    {   
        "src":"de"
        "target":["en", "fr"]
        "content": [{
            "text": "Ich würde wirklich gern Ihr Auto um den Block fahren ein paar Mal."
        },
        {
            "text": "Hello World"
        }]
    }

    """
    body = request.get_json(force=True)
    translation_obj = translation_api_request(AZURE_TRANSLATOR_TRANSLATE_ROUTE,body['content'], src=body['src'], targets=body['targets'])
    return jsonify(translation_obj)


@translator.route('/detect', methods = ['POST'])
def detect_language():
    '''
    Detects the language using the same logic as the translation API call, but with 
    different params passed to the Azure Translator API. For our current purposes
    we only need to detect the language of the entire document, so we simply pass in 
    one text document as a request body. Note from the example below that you can actually
    pass in any number of them. 
    body must have the below format, e.g. just the "content" value from the translation
    route: 
        [{
            'text': 'Ich würde wirklich gern Ihr Auto um den Block fahren ein paar Mal.'
        },
        {
            'text': 'Hello World'
        }]
    '''
    body = request.get_json(force=True)
    
    language_guess = translation_api_request(AZURE_TRANSLATOR_DETECT_ROUTE,body)

    return jsonify(language_guess)

