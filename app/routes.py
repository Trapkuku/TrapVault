from flask import Blueprint, render_template, redirect, url_for, flash, request, send_from_directory, abort, current_app
import os
from app import db
from flask_login import login_user, logout_user, login_required, current_user
from app.models import User, File, Folder, Backup
from werkzeug.utils import secure_filename
import datetime
import zipfile

bp = Blueprint('main', __name__)

ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@bp.route('/')
def index():
    return render_template('index.html')

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username'].strip()
        email = request.form['email'].strip()
        password = request.form['password']
        confirm_password = request.form['confirm-password']

        if password != confirm_password:
            flash('Пароли не совпадают!')
            return redirect(url_for('main.register'))

        if User.query.filter((User.username == username) | (User.email == email)).first():
            flash('Пользователь с таким именем или email уже существует!')
            return redirect(url_for('main.register'))

        new_user = User(username=username, email=email)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        flash('Регистрация прошла успешно! Можете войти в систему.')
        return redirect(url_for('main.login'))

    return render_template('register.html')

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        identifier = request.form['username'].strip()
        password = request.form['password']
        user = User.query.filter((User.username == identifier) | (User.email == identifier)).first()

        if user is None or not user.check_password(password):
            flash('Неверное имя пользователя, email или пароль!')
            return redirect(url_for('main.login'))

        login_user(user)
        return redirect(url_for('main.profile'))

    return render_template('login.html')

@bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('Нет файла для загрузки')
            return redirect(url_for('main.profile'))

        file = request.files['file']

        if file.filename == '' or not allowed_file(file.filename):
            flash('Файл не выбран или имеет неверный формат')
            return redirect(url_for('main.profile'))

        folder_id = request.form.get('folder_id')
        folder = Folder.query.get(folder_id) if folder_id else None

        base_user_path = os.path.join(current_app.config['UPLOAD_FOLDER'], current_user.username)
        if not os.path.exists(base_user_path):
            os.makedirs(base_user_path)

        if folder:
            folder_path = os.path.join(base_user_path, folder.name)
        else:
            folder_path = base_user_path

        if not os.path.exists(folder_path):
            os.makedirs(folder_path)

        filename = secure_filename(file.filename)
        file_path = os.path.join(folder_path, filename)
        file.save(file_path)

        new_file = File(filename=filename, user_id=current_user.id, folder=folder)
        db.session.add(new_file)
        db.session.commit()

        flash('Файл успешно загружен')
        return redirect(url_for('main.profile'))

    files = File.query.filter_by(user_id=current_user.id, folder_id=None).all()
    folders = Folder.query.filter_by(user_id=current_user.id).all()
    return render_template('profile.html', username=current_user.username, email=current_user.email, files=files, folders=folders)

@bp.route('/delete_file/<int:file_id>', methods=['POST'])
@login_required
def delete_file(file_id):
    file = File.query.get_or_404(file_id)
    if file.user_id != current_user.id:
        flash('У вас нет прав для удаления этого файла')
        return redirect(url_for('main.profile'))

    user_folder_path = os.path.join(current_app.config['UPLOAD_FOLDER'], current_user.username)
    if file.folder:
        folder_path = os.path.join(user_folder_path, file.folder.name)
    else:
        folder_path = user_folder_path

    file_path = os.path.join(folder_path, file.filename)

    if os.path.exists(file_path):
        os.remove(file_path)

    db.session.delete(file)
    db.session.commit()
    flash('Файл успешно удален')
    return redirect(url_for('main.profile'))

@bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы успешно вышли из системы.')
    return redirect(url_for('main.index'))

@bp.route('/download/<int:file_id>')
@login_required
def download_file(file_id):
    file = File.query.get_or_404(file_id)
    if file.user_id != current_user.id:
        flash('У вас нет прав для скачивания этого файла')
        return redirect(url_for('main.profile'))

    user_folder_path = os.path.join(current_app.config['UPLOAD_FOLDER'], current_user.username)
    if file.folder:
        folder_path = os.path.join(user_folder_path, file.folder.name)
    else:
        folder_path = user_folder_path
    return send_from_directory(folder_path, file.filename, as_attachment=True)

@bp.route('/create_folder', methods=['POST'])
@login_required
def create_folder():
    folder_name = request.form.get('folder_name', '').strip()
    if not folder_name:
        flash('Имя папки не может быть пустым')
        return redirect(url_for('main.profile'))

    user_folder_path = os.path.join(current_app.config['UPLOAD_FOLDER'], current_user.username)
    if not os.path.exists(user_folder_path):
        os.makedirs(user_folder_path)

    folder_path = os.path.join(user_folder_path, folder_name)
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
        new_folder = Folder(name=folder_name, user_id=current_user.id)
        db.session.add(new_folder)
        db.session.commit()
        flash(f'Папка "{folder_name}" успешно создана')
    else:
        flash('Папка с таким именем уже существует')

    return redirect(url_for('main.profile'))

@bp.route('/folder/<int:folder_id>', methods=['GET', 'POST'])
@login_required
def view_folder(folder_id):
    folder = Folder.query.get_or_404(folder_id)
    if folder.user_id != current_user.id:
        flash('У вас нет прав для доступа к этой папке')
        return redirect(url_for('main.profile'))

    if request.method == 'POST':
        if 'file' not in request.files:
            flash('Нет файла для загрузки')
            return redirect(url_for('main.view_folder', folder_id=folder_id))

        file = request.files['file']

        if file.filename == '' or not allowed_file(file.filename):
            flash('Файл не выбран или имеет неверный формат')
            return redirect(url_for('main.view_folder', folder_id=folder_id))

        folder_path = os.path.join(current_app.config['UPLOAD_FOLDER'], current_user.username, folder.name)

        if not os.path.exists(folder_path):
            os.makedirs(folder_path)

        filename = secure_filename(file.filename)
        file.save(os.path.join(folder_path, filename))

        new_file = File(filename=filename, user_id=current_user.id, folder=folder)
        db.session.add(new_file)
        db.session.commit()

        flash('Файл успешно загружен')
        return redirect(url_for('main.view_folder', folder_id=folder_id))

    files = File.query.filter_by(folder_id=folder.id).all()
    return render_template('folder.html', folder=folder, files=files)

@bp.route('/folders', methods=['GET', 'POST'])
@login_required
def view_folders():
    if request.method == 'POST':
        folder_name = request.form.get('folder_name', '').strip()
        if not folder_name:
            flash('Имя папки не может быть пустым')
            return redirect(url_for('main.view_folders'))

        user_folder_path = os.path.join(current_app.config['UPLOAD_FOLDER'], current_user.username)
        if not os.path.exists(user_folder_path):
            os.makedirs(user_folder_path)

        folder_path = os.path.join(user_folder_path, folder_name)
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
            new_folder = Folder(name=folder_name, user_id=current_user.id)
            db.session.add(new_folder)
            db.session.commit()
            flash(f'Папка "{folder_name}" успешно создана')
        else:
            flash('Папка с таким именем уже существует')

        return redirect(url_for('main.view_folders'))

    folders = Folder.query.filter_by(user_id=current_user.id).all()
    return render_template('folders.html', folders=folders)

@bp.route('/search_folders', methods=['GET'])
@login_required
def search_folders():
    query = request.args.get('query', '').strip().lower()
    folders = []
    files = []

    if query:
        folders = Folder.query.filter(Folder.user_id == current_user.id, Folder.name.ilike(f"%{query}%")).all()
        files = File.query.filter(File.user_id == current_user.id, File.filename.ilike(f"%{query}%")).all()
    else:
        folders = Folder.query.filter_by(user_id=current_user.id).all()
        files = File.query.filter_by(user_id=current_user.id).all()

    folders_data = [{'id': folder.id, 'name': folder.name} for folder in folders]
    files_data = [{'id': file.id, 'filename': file.filename, 'folder_name': file.folder.name if file.folder else ''} for file in files]

    return {
        'folders': folders_data,
        'files': files_data
    }

@bp.route('/delete_folder/<int:folder_id>', methods=['POST'])
@login_required
def delete_folder(folder_id):
    folder = Folder.query.get_or_404(folder_id)
    if folder.user_id != current_user.id:
        flash('У вас нет прав для удаления этой папки')
        return redirect(url_for('main.view_folders'))

    user_folder_path = os.path.join(current_app.config['UPLOAD_FOLDER'], current_user.username, folder.name)

    # Удаляем все файлы в папке
    files = File.query.filter_by(folder_id=folder.id).all()
    for file_obj in files:
        file_path = os.path.join(user_folder_path, file_obj.filename)
        if os.path.exists(file_path):
            os.remove(file_path)
        db.session.delete(file_obj)

    db.session.delete(folder)
    db.session.commit()

    # Удаляем физическую директорию папки, если она пуста
    if os.path.exists(user_folder_path) and not os.listdir(user_folder_path):
        os.rmdir(user_folder_path)

    flash('Папка успешно удалена')
    return redirect(url_for('main.view_folders'))

@bp.route('/upload_avatar', methods=['POST'])
@login_required
def upload_avatar():
    if 'avatar' not in request.files:
        flash('Нет файла для загрузки')
        return redirect(url_for('main.profile'))

    file = request.files['avatar']

    if file.filename == '' or not allowed_file(file.filename):
        flash('Файл не выбран или имеет неверный формат')
        return redirect(url_for('main.profile'))

    user_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], current_user.username, 'avatars')
    if not os.path.exists(user_folder):
        os.makedirs(user_folder)

    # Удаление предыдущего аватара
    if current_user.avatar:
        previous_avatar_path = os.path.join(current_app.config['UPLOAD_FOLDER'], current_user.avatar.replace('/', os.sep))
        if os.path.exists(previous_avatar_path):
            os.remove(previous_avatar_path)

    filename = secure_filename(file.filename)
    avatar_path = os.path.join(user_folder, filename)
    file.save(avatar_path)

    relative_path = os.path.join(current_user.username, 'avatars', filename)
    relative_path = relative_path.replace('\\', '/')
    current_user.avatar = relative_path
    db.session.commit()

    flash('Аватар успешно обновлён')
    return redirect(url_for('main.profile'))

@bp.route('/remove_avatar', methods=['POST'])
@login_required
def remove_avatar():
    if current_user.avatar:
        avatar_path = os.path.join(current_app.config['UPLOAD_FOLDER'], current_user.avatar.replace('/', os.sep))
        if os.path.exists(avatar_path):
            os.remove(avatar_path)

    current_user.avatar = None
    db.session.commit()
    flash('Аватар удалён')
    return redirect(url_for('main.profile'))

@bp.route('/uploads/<path:filename>')
@login_required
def uploaded_file(filename):
    uploads_path = os.path.join(current_app.config['UPLOAD_FOLDER'])
    return send_from_directory(uploads_path, filename)

@bp.route('/create_backup', methods=['GET'])
@login_required
def create_backup():
    backup_folder = os.path.join(current_app.root_path, 'backups')
    if not os.path.exists(backup_folder):
        os.makedirs(backup_folder)

    user_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], current_user.username)
    if not os.path.exists(user_folder) or not any(os.scandir(user_folder)):
        flash('Нет данных для резервного копирования.', 'warning')
        return redirect(url_for('main.profile'))

    backup_filename = f"backup_{current_user.username}_{datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S')}.zip"
    backup_path = os.path.join(backup_folder, backup_filename)

    try:
        with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as backup_zip:
            for root, dirs, files in os.walk(user_folder):
                for f in files:
                    file_path = os.path.join(root, f)
                    arcname = os.path.relpath(file_path, user_folder)
                    backup_zip.write(file_path, arcname)

        new_backup = Backup(user_id=current_user.id, backup_file=backup_filename)
        db.session.add(new_backup)
        db.session.commit()

        flash('Резервная копия успешно создана!', 'success')
    except Exception as e:
        flash(f'Ошибка при создании резервной копии: {str(e)}', 'danger')

    return redirect(url_for('main.profile'))

@bp.route('/restore_backup/<int:backup_id>', methods=['POST'])
@login_required
def restore_backup(backup_id):
    backup = Backup.query.get_or_404(backup_id)

    if backup.user_id != current_user.id:
        flash('У вас нет прав для восстановления этой резервной копии')
        return redirect(url_for('main.profile'))

    backup_path = os.path.join(current_app.root_path, 'backups', backup.backup_file)
    user_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], current_user.username)

    if not os.path.exists(backup_path):
        flash('Резервная копия не найдена')
        return redirect(url_for('main.profile'))

    try:
        # Очистка текущей папки пользователя
        if os.path.exists(user_folder):
            for root, dirs, files in os.walk(user_folder, topdown=False):
                for f in files:
                    os.remove(os.path.join(root, f))
                for d in dirs:
                    os.rmdir(os.path.join(root, d))

        # Извлечение резервной копии
        with zipfile.ZipFile(backup_path, 'r') as backup_zip:
            backup_zip.extractall(user_folder)

        File.query.filter_by(user_id=current_user.id).delete()
        Folder.query.filter_by(user_id=current_user.id).delete()
        db.session.commit()

        # Восстанавливаем данные в базе
        for root, dirs, files in os.walk(user_folder):
            current_folder_name = os.path.basename(root)

            if root == user_folder:
                continue

            if current_folder_name == 'avatars':
                # Аватары не считаем папкой пользователя
                pass
            else:
                # Создаём запись для папок
                for folder_name in dirs:
                    if folder_name != 'avatars':
                        folder_in_db = Folder.query.filter_by(name=folder_name, user_id=current_user.id).first()
                        if not folder_in_db:
                            new_folder = Folder(name=folder_name, user_id=current_user.id)
                            db.session.add(new_folder)
                            db.session.flush()

            parent_folder = Folder.query.filter_by(name=current_folder_name, user_id=current_user.id).first()
            if current_folder_name != 'avatars':
                if not parent_folder and current_folder_name != os.path.basename(user_folder):
                    parent_folder = Folder(name=current_folder_name, user_id=current_user.id)
                    db.session.add(parent_folder)
                    db.session.flush()

            for f in files:
                if current_folder_name == 'avatars' and current_user.avatar and f == os.path.basename(current_user.avatar):
                    current_user.avatar = os.path.join(current_user.username, 'avatars', f).replace('\\', '/')
                if parent_folder and current_folder_name != 'avatars':
                    file_in_db = File.query.filter_by(filename=f, user_id=current_user.id).first()
                    if not file_in_db:
                        new_file = File(filename=f, user_id=current_user.id, folder=parent_folder)
                        db.session.add(new_file)

        db.session.commit()
        flash('Резервная копия успешно восстановлена', 'success')
    except Exception as e:
        flash(f'Ошибка при восстановлении резервной копии: {str(e)}', 'danger')

    return redirect(url_for('main.profile'))

@bp.route('/delete_backup/<int:backup_id>', methods=['POST'])
@login_required
def delete_backup(backup_id):
    backup = Backup.query.get_or_404(backup_id)

    if backup.user_id != current_user.id:
        flash('У вас нет прав для удаления этой резервной копии.', 'danger')
        return redirect(url_for('main.profile'))

    backup_path = os.path.join(current_app.root_path, 'backups', backup.backup_file)
    if os.path.exists(backup_path):
        os.remove(backup_path)

    db.session.delete(backup)
    db.session.commit()

    flash('Резервная копия успешно удалена.', 'success')
    return redirect(url_for('main.profile'))
