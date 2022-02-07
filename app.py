from flask import Flask
from consents_api import consents_api
from translator import translator
from flask_migrate import Migrate
import os
from dotenv import load_dotenv
load_dotenv()

from models import db

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI']= os.environ.get('SQLALCHEMY_DATABASE_URI')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)
with app.app_context():
    db.drop_all()
    db.create_all()

app.register_blueprint(consents_api)
app.register_blueprint(translator)


if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0")
