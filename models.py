"""
We have a soft delete option for both Consents and ConsentSections so that 
we largely avoid the problem of orphaned sections.  
"""

# Note that we create a separate database extension here to avoid a circular import with 
# app.py
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from marshmallow import Schema, fields

db = SQLAlchemy()

# Enum doesn't work, reverting to db.String type for lang,
# TODO: figure out how to make this work, or just use validation syntax to accomplish
# The same thing with db.String()
# # creating enumerations using class
# class Language(enum.Enum):
#     EN: str = 'en'
#     ES: str = 'es'
#     FR: str = 'fr'

class Consent(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.now)
    soft_deleted_at = db.Column(db.DateTime)
    consent_sections = db.relationship('ConsentSection', backref='consent', lazy=True)

    # I know I should be using a 'deletable' interface here.
    def soft_delete(self): 
        if self.soft_deleted_at != None:
            self.soft_deleted_at = datetime.now()

    def hard_delete(self): 
        db.session.delete(self)


class ConsentSection(db.Model):
    id = db.Column(db.Integer, primary_key=True,autoincrement=True)
    consent_id = db.Column(db.Integer, db.ForeignKey('consent.id'))
    title = db.Column(db.String(200))
    content = db.Column(db.Text, nullable=False)
    lang = db.Column(db.String(2))
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.now)
    soft_deleted_at = db.Column(db.DateTime)
    section_translations = db.relationship('SectionTranslation', backref='consent_section', lazy=True)

    def soft_delete(self): 
        if self.soft_deleted_at != None:
            self.soft_deleted_at = datetime.now()

    def hard_delete(self): 
        db.session.delete(self)

class SectionTranslation(db.Model): 
    id = db.Column(db.Integer, primary_key=True,autoincrement=True)
    section_id = db.Column(db.Integer, db.ForeignKey('consent_section.id'))
    title = db.Column(db.String(200))
    content = db.Column(db.Text, nullable=False)
    lang = db.Column(db.String(2))
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.now)
    soft_deleted_at = db.Column(db.DateTime)

    def soft_delete(self): 
        if self.soft_deleted_at != None:
            self.soft_deleted_at = datetime.now()

    def hard_delete(self): 
        db.session.delete(self)


class ConsentSchema(Schema):
    class Meta:
        fields = (
                'id',
                'created_at',
                'soft_deleted_at',
                )
class ConsentSectionSchema(Schema):
    class Meta:
        fields = (
                'id', 
                'consent_id', 
                'title', 
                'content', 
                'lang',
                'soft_deleted_at', 
                )

class SectionTranslationSchema(Schema):
    class Meta:
        fields = (
                'id', 
                'section_id', 
                'title', 
                'content', 
                'lang',
                'soft_deleted_at', 
                )

"""
If you want to shield some of the fields from display in the "return a translated consent"
route. 
"""
# class DisplaySectionTranslationSchema(Schema):
#     class Meta:
#         fields = (
#                 'id', 
#                 'title', 
#                 'content', 
#                 )


consent_schema = ConsentSchema()
consents_schema = ConsentSchema(many=True)

consent_section_schema = ConsentSectionSchema()
consent_sections_schema = ConsentSectionSchema(many=True)

section_translation_schema = SectionTranslationSchema()
section_translations_schema = SectionTranslationSchema(many=True)




