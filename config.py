import os

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Путь к директории загрузок
    UPLOAD_FOLDER = os.path.join(basedir, 'app', 'uploads')
    # Путь к директории резервных копий
    BACKUP_FOLDER = os.path.join(basedir, 'app', 'backups')