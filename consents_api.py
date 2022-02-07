from flask import Blueprint, jsonify, request, Response
import requests
import json
from models import (
                    Consent, 
                    ConsentSection, 
                    SectionTranslation,
                    consent_schema, 
                    consents_schema, 
                    consent_section_schema, 
                    consent_sections_schema,
                    section_translation_schema,
                    section_translations_schema,
                    )
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from dotenv import load_dotenv
import os

load_dotenv()

SUPPORTED_LANGUAGES_STR = os.environ.get('SUPPORTED_LANGUAGES_STR')
SUPPORTED_LANGUAGES = json.loads(SUPPORTED_LANGUAGES_STR)
PROD_MODE = 'PROD'
DEV_MODE = 'DEV'
APP_MODE = os.environ.get('APP_MODE')

# Note that a forward slash (/) is added to the URL on render, so no need to add it yourself
# in a format string
PROD_BASE_URL = os.environ.get('PROD_BASE_URL')

if APP_MODE and APP_MODE == DEV_MODE :
    PROD_BASE_URL += '/'

   
db = SQLAlchemy()

def get_corpus(section): 
    """
    Intended originally to concatenate all sections of a Consent Form Data Object for 
    detecting the language. 
    Currently used just to detect the language from the first section.
    """
    return section['title'].join(section['content'])

def detect_language(corpus):
    """
    Detects the language using azure translator api, returns falsy value if confidence_score
    not high enough.
    """
    request_body = [{'text': corpus}]
    headers = {
        'Content-type': 'application/json'
    }
    lang_resp_raw = requests.post(f"{PROD_BASE_URL}detect", headers=headers, json=request_body) 
    lang_resp = lang_resp_raw.json()
    score = lang_resp[0]['score']
    detected_lang = lang_resp[0]['language']
    if score > .6:
        return detected_lang
    else:
        return None

def translate_consent_section(cs, src='en', targets=SUPPORTED_LANGUAGES):
    request_body = {}
    request_body['src'] = src
    request_body['targets'] = targets
    # Note we must store an array of text documents in the 'content' property. 
    request_body['content'] = [{
        'text': cs.title
    },
    {
        'text': cs.content
    }]
    headers = {
        'Content-type': 'application/json'
    }
    resp = requests.post(f"{PROD_BASE_URL}translate", headers=headers, json=request_body) 
    translation_list = resp.json()
    for i in range(len(request_body['targets'])): 
        new_trans_lang = translation_list[0]['translations'][i]['to']
        new_trans_title_text = translation_list[0]['translations'][i]['text']
        new_trans_content_text = translation_list[1]['translations'][i]['text']
        new_trans = SectionTranslation(section_id=cs.id, lang=new_trans_lang, title = new_trans_title_text, content=new_trans_content_text)
        db.session.add(new_trans)
    db.session.commit()

"""
We pass in the global app variable "__name__" to the Blueprint object to make this 
file a blueprint.  
"""
consents_api = Blueprint('consents_api', __name__)

@consents_api.route('/')
def index():
    return Response("Here's the main",status=200)

@consents_api.route('/consents/')
def get_consents():
    consents =  Consent.query.all()
    if len(consents)>0 :
        return Response(consents_schema.dumps(consents), 200)
    else:
        return jsonify([])



"""
Creates a new consent form content object and its corresponding sections. When a 
consent form is created, it is instantly translated into Spanish and French and 
two new SectionTranslation objects are persisted. 

TODO: set up cron job for translation so that more languages can be supported. 
"""
@consents_api.route('/consents/', methods=['POST'])
def create_consent():
    body = request.get_json()
    sections_to_make = body['sections']
    new_consent = Consent(created_at = datetime.now())
    db.session.add(new_consent)
    db.session.commit()
    src_lang = None
    for section in sections_to_make: 
        new_consent_sec = ConsentSection(title = section['title'], content=section['content'], consent_id = new_consent.id)
        # We need to add the new consent to the db first to populate the primary key for the id
        db.session.add(new_consent_sec)
        db.session.commit()  
        if not src_lang:      
            if "lang" in body:
                src_lang = body['lang']
            else:
                corpus = get_corpus(section)
                lang = detect_language(corpus)
                if lang: 
                    src_lang = lang
                else: 
                    return Response("Could not detect a language reliabily enough, created consent form data object with unknown language", 201)
        translate_consent_section(new_consent_sec, src=src_lang)
    db.session.commit()
    return Response(consent_schema.dump(new_consent), 200)


"""
We could use the uuid converter to shield the primary keys, but for ease of use we don't
do that here. 
Note that we don't use the events api to check if a consent is being got and check its 
deletion status. This is overkill for our needs, since there's not many if statements 
we need to add to check for non-soft-deletion
"""

@consents_api.route('/consents/<consent_id>')
def get_consent(consent_id):
    consent =  Consent.query.get_or_404(consent_id)
    if not consent.soft_deleted_at: 
        return Response(consent_schema.dump(consent), 200)
    else: 
        return Response("Consent form data does not exist", 404)


"""
Note that for soft deletion, we don't actually need to do anything to the consent sections.
They still are associated with the deleted consent's id if we ever want to restore that consent. 
"""
@consents_api.route('/consents/<consent_id>', methods=['DELETE'])
def soft_delete_consent(consent_id):
    consent =  Consent.query.get_or_404(consent_id)
    if not consent.soft_deleted_at:
        consent.soft_deleted_at = datetime.now()
        db.session.merge(consent)
        db.session.commit()
        return Response("Consent form data successfully deleted!", 200)
    else: 
        return Response("Consent form does not exist", 404)

"""
For hard deletion, we don't care whether the consent is soft deleted. We also 
rely on get_or_404 to find out whether a valid consent_id has been given.

Hard delete is broken due to not starting out by turning the flask app into a package
and utilizing a functional __init__.py. This results in multiple db sessions being necessary
creating duplicates and merge problems.
"""
@consents_api.route('/consents/<consent_id>/hard_delete_not_for_the_faint_of_heart', methods=['DELETE'])
def hard_delete_consent(consent_id):
    consent =  Consent.query.get_or_404(consent_id)
    sections = ConsentSection.query.filter(ConsentSection.consent_id == consent_id)
    for section in sections:
        db.session.merge(section)
        db.session.delete(section)
        db.session.merge(section)
        db.session.commit()
    db.session.merge(consent)
    db.session.delete(consent)  
    db.session.merge(consent)
    db.commit()
    return Response("Succesfully hard deleted consent form data.", 200)


"""
This route obtains the specified consent in the target language.
If the target language is not one of the supported languages in the db, an attempt 
is made to translate the consent into that language and the translation is stored, 
but these translation objects are not really supported currently, and may wreak havoc. 

<lang> is a 2 character ISO 6391 string representing the language. 
"""
@consents_api.route('/consents/<consent_id>/<lang>')
def get_consent_in_lang(consent_id, lang):
    consent = Consent.query.get_or_404(consent_id)
    sections = ConsentSection.query.filter(ConsentSection.consent_id == consent_id)
    if not consent.soft_deleted_at: 
        if lang in SUPPORTED_LANGUAGES:      
            sections_translated = []
            for section in sections: 
                sections_translated.append(SectionTranslation.query.filter(SectionTranslation.section_id == section.id, SectionTranslation.lang == lang).first_or_404())
            resp = section_translations_schema.dumps(sections_translated)
            return Response(resp, 200)
        else: 
            sections_translated = []
            for section in sections: 
                translate_consent_section(section, src=section.lang, targets=[lang])
            resp = section_translations_schema.dumps(sections_translated)
            return Response(resp, 200)
    else: 
        return Response("Consent form data does not exist", 404)


# Possibly not the most efficient way to do this.
@consents_api.route('/consents/<consent_id>/sections')
def get_consent_sections(consent_id): 
    consent = Consent.query.get_or_404(consent_id)
    if not consent.soft_deleted_at:
        return Response(consent_sections_schema.dumps(consent.consent_sections), 200)
    else: 
        return jsonify([])

@consents_api.route('/sections/')
def get_sections(): 
    sections = ConsentSection.query.all()
    if len(sections) > 0 : 
        return Response(consent_sections_schema.dumps(sections), 200)
    else:
        return jsonify([])

@consents_api.route('/sections/<section_id>')
def get_section(section_id): 
    section = ConsentSection.query.get_or_404(section_id)
    return consent_section_schema.dump(section)

"""
This route updates individual sections by id. Once updated, 
new translations are generated for the corresponding section. 
Note that to obtain the section id you want to update, you can use the 
/consents/<consent_id>/sections route to determine the right one. This seems
to be the most straight forward implementation, rather than forcing you to 
copy and paste tons of section text that you don't want to update and take up 
bandwidth
"""

@consents_api.route('/sections/<section_id>', methods=["PUT"])
def update_section(section_id): 
    body = request.get_json()
    try: 
        new_consent_section = ConsentSection.query.get_or_404(section_id)
        new_consent_section.title = body['title']
        new_consent_section.content = body['content']
        db.session.merge(new_consent_section)
        db.session.commit() 
        old_translations = SectionTranslation.query.filter(SectionTranslation.section_id == section_id)
        for translation in old_translations: 
            translation.soft_deleted_at = datetime.now()
            db.session.merge(translation)
            db.session.commit()
        translate_consent_section(new_consent_section)
    except Exception as err:
        print("Encountered exception. {}".format(err))
    return Response("success!", 200)


@consents_api.route('/sections/<section_id>/translations')
def get_section_translations(section_id): 
    undeleted_section_translations = SectionTranslation.query.filter(
                                                                SectionTranslation.section_id == int(section_id), SectionTranslation.soft_deleted_at == None)
    if undeleted_section_translations.first():
        return Response(section_translations_schema.dumps(undeleted_section_translations), 200)
    else:
        return jsonify([])

@consents_api.route('/translations/')
def get_translations(): 
    translations = SectionTranslation.query.all()
    if len(translations) > 0:
        return Response(section_translations_schema.dumps(translations), 200)
    else: 
        return jsonify([])


@consents_api.route('/translations/<translation_id>')
def get_translation(translation_id): 
    translation = SectionTranslation.query.get_or_404(translation_id)
    return Response(section_translation_schema.dump(translation), 200)


        