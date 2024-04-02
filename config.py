import os
import platform
SECRET_KEY = os.urandom(32)
# Grabs the folder where the script runs.
basedir = os.path.abspath(os.path.dirname(__file__))

# Enable debug mode.
DEBUG = True

# Connect to the database


## TODO IMPLEMENT DATABASE URL
if platform.system() == 'Windows':
    # For Windows Environment
    SQLALCHEMY_DATABASE_URI = 'postgresql://postgres:1234@localhost:5432/fyyur'
else:
    # For linux Environment
    SQLALCHEMY_DATABASE_URI = 'postgresql://postgres@localhost:5432/fyyur'


##  Track Modifications
SQLALCHEMY_TRACK_MODIFICATIONS = False
WTF_CSRF_ENABLED = True