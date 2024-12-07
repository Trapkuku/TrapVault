from flask import Flask
from .extensions import db, migrate, login_manager
from .models import User
import os
def create_app():
    app = Flask(__name__)
    app.config.from_object('config.Config')
    app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'uploads')

    # Инициализация расширений
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = 'main.login'

    # Регистрация маршрутов
    from app.routes import bp as main_bp
    app.register_blueprint(main_bp)
    return app

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
