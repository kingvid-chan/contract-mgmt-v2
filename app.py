import os
import uuid
from functools import wraps

import bcrypt
from flask import (
    Flask, Blueprint, render_template, request, redirect,
    url_for, flash, send_from_directory, after_this_request, current_app
)
from flask_login import (
    LoginManager, login_user, logout_user, login_required, current_user
)

from config import Config
from models import db, User, Contract, Attachment


def create_app():
    app = Flask(__name__, static_folder="static", template_folder="templates")
    app.config.from_object(Config)

    # Ensure required directories exist
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(os.path.join(app.root_path, "data"), exist_ok=True)

    db.init_app(app)

    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = "main.login"

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # ---- Blueprint with base_path ----
    main_bp = Blueprint("main", __name__, url_prefix=Config.BASE_PATH,
                        static_folder="static", static_url_path="/static")

    # ---- Decorators ----
    def admin_required(f):
        @wraps(f)
        @login_required
        def decorated(*args, **kwargs):
            if not current_user.is_admin():
                flash("需要管理员权限", "danger")
                return redirect(url_for("main.dashboard"))
            return f(*args, **kwargs)
        return decorated

    def allowed_file(filename):
        return "." in filename and \
               filename.rsplit(".", 1)[1].lower() in Config.ALLOWED_EXTENSIONS

    # ---- After-request: Cache-Control for HTML ----
    @main_bp.after_request
    def add_cache_control(response):
        if response.content_type and "text/html" in response.content_type:
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response

    # Context processor: make version and base_path available to all templates
    @main_bp.context_processor
    def inject_globals():
        return {
            "version": Config.VERSION,
            "base_path": Config.BASE_PATH,
        }

    # ---- Health Check ----
    @main_bp.route("/healthz")
    def healthz():
        return {"status": "ok", "version": Config.VERSION}

    # ---- Auth Routes ----
    @main_bp.route("/auth/login", methods=["GET", "POST"])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for("main.dashboard"))
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "").encode("utf-8")
            user = User.query.filter_by(username=username).first()
            if user and user.is_active and \
                    bcrypt.checkpw(password, user.password_hash.encode("utf-8")):
                login_user(user)
                flash(f"欢迎回来，{user.username}！", "success")
                next_page = request.args.get("next")
                return redirect(next_page or url_for("main.dashboard"))
            flash("用户名或密码错误，或账号已被禁用", "danger")
        return render_template("login.html")

    @main_bp.route("/auth/register", methods=["GET", "POST"])
    def register():
        if current_user.is_authenticated:
            return redirect(url_for("main.dashboard"))
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            confirm = request.form.get("confirm_password", "")

            errors = []
            if not username or len(username) < 2:
                errors.append("用户名至少 2 个字符")
            if not password or len(password) < 4:
                errors.append("密码至少 4 个字符")
            if password != confirm:
                errors.append("两次密码输入不一致")
            if User.query.filter_by(username=username).first():
                errors.append("用户名已存在")

            if errors:
                for e in errors:
                    flash(e, "danger")
                return render_template("register.html")

            hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
            user = User(username=username, password_hash=hashed.decode("utf-8"), role="user")
            db.session.add(user)
            db.session.commit()
            flash("注册成功，请登录", "success")
            return redirect(url_for("main.login"))
        return render_template("register.html")

    @main_bp.route("/auth/logout")
    @login_required
    def logout():
        logout_user()
        flash("已退出登录", "info")
        return redirect(url_for("main.login"))

    # ---- Dashboard / Contract List ----
    @main_bp.route("/")
    @login_required
    def dashboard():
        if current_user.is_admin():
            contracts = Contract.query.order_by(Contract.updated_at.desc()).all()
        else:
            contracts = Contract.query.filter_by(user_id=current_user.id) \
                                       .order_by(Contract.updated_at.desc()).all()
        return render_template("dashboard.html", contracts=contracts)

    # ---- Contract Create ----
    @main_bp.route("/contracts/create", methods=["GET", "POST"])
    @login_required
    def contract_create():
        if request.method == "POST":
            title = request.form.get("title", "").strip()
            counterparty = request.form.get("counterparty", "").strip()
            amount = request.form.get("amount", "").strip() or None

            errors = []
            if not title:
                errors.append("合同标题不能为空")
            if not counterparty:
                errors.append("对方单位不能为空")

            if errors:
                for e in errors:
                    flash(e, "danger")
                return render_template("contract_form.html", contract=None)

            contract = Contract(
                title=title,
                description=request.form.get("description", "").strip(),
                counterparty=counterparty,
                amount=amount,
                status=request.form.get("status", "draft"),
                user_id=current_user.id,
            )
            db.session.add(contract)
            db.session.commit()

            # Handle attachment upload
            file = request.files.get("attachment")
            if file and file.filename and allowed_file(file.filename):
                _save_attachment(file, contract)

            flash("合同创建成功", "success")
            return redirect(url_for("main.contract_detail", contract_id=contract.id))
        return render_template("contract_form.html", contract=None)

    # ---- Contract Detail ----
    @main_bp.route("/contracts/<int:contract_id>")
    @login_required
    def contract_detail(contract_id):
        contract = db.session.get(Contract, contract_id)
        if not contract:
            flash("合同不存在", "danger")
            return redirect(url_for("main.dashboard"))
        if not current_user.is_admin() and contract.user_id != current_user.id:
            flash("无权访问此合同", "danger")
            return redirect(url_for("main.dashboard"))
        attachments = contract.attachments.all()
        return render_template("contract_detail.html", contract=contract,
                               attachments=attachments)

    # ---- Contract Edit ----
    @main_bp.route("/contracts/<int:contract_id>/edit", methods=["GET", "POST"])
    @login_required
    def contract_edit(contract_id):
        contract = db.session.get(Contract, contract_id)
        if not contract:
            flash("合同不存在", "danger")
            return redirect(url_for("main.dashboard"))
        if not current_user.is_admin() and contract.user_id != current_user.id:
            flash("无权编辑此合同", "danger")
            return redirect(url_for("main.dashboard"))

        if request.method == "POST":
            title = request.form.get("title", "").strip()
            counterparty = request.form.get("counterparty", "").strip()

            if not title or not counterparty:
                flash("合同标题和对方单位不能为空", "danger")
                return render_template("contract_form.html", contract=contract)

            contract.title = title
            contract.description = request.form.get("description", "").strip()
            contract.counterparty = counterparty
            contract.amount = request.form.get("amount", "").strip() or None
            contract.status = request.form.get("status", "draft")
            db.session.commit()

            # Handle new attachment upload
            file = request.files.get("attachment")
            if file and file.filename and allowed_file(file.filename):
                _save_attachment(file, contract)

            flash("合同更新成功", "success")
            return redirect(url_for("main.contract_detail", contract_id=contract.id))
        return render_template("contract_form.html", contract=contract)

    # ---- Contract Delete ----
    @main_bp.route("/contracts/<int:contract_id>/delete", methods=["POST"])
    @login_required
    def contract_delete(contract_id):
        contract = db.session.get(Contract, contract_id)
        if not contract:
            flash("合同不存在", "danger")
            return redirect(url_for("main.dashboard"))
        if not current_user.is_admin() and contract.user_id != current_user.id:
            flash("无权删除此合同", "danger")
            return redirect(url_for("main.dashboard"))

        # Delete attachment files from disk
        for attachment in contract.attachments.all():
            _delete_attachment_file(attachment)

        db.session.delete(contract)
        db.session.commit()
        flash("合同已删除", "info")
        return redirect(url_for("main.dashboard"))

    # ---- Attachment Upload ----
    @main_bp.route("/contracts/<int:contract_id>/attachments/upload", methods=["POST"])
    @login_required
    def attachment_upload(contract_id):
        contract = db.session.get(Contract, contract_id)
        if not contract:
            flash("合同不存在", "danger")
            return redirect(url_for("main.dashboard"))
        if not current_user.is_admin() and contract.user_id != current_user.id:
            flash("无权操作此合同", "danger")
            return redirect(url_for("main.dashboard"))

        file = request.files.get("attachment")
        if not file or not file.filename:
            flash("请选择文件", "danger")
            return redirect(url_for("main.contract_detail", contract_id=contract.id))

        if not allowed_file(file.filename):
            flash("仅支持 PDF、DOC、DOCX 格式", "danger")
            return redirect(url_for("main.contract_detail", contract_id=contract.id))

        _save_attachment(file, contract)
        flash("附件上传成功", "success")
        return redirect(url_for("main.contract_detail", contract_id=contract.id))

    # ---- Attachment Download ----
    @main_bp.route("/attachments/<int:attachment_id>/download")
    @login_required
    def attachment_download(attachment_id):
        attachment = db.session.get(Attachment, attachment_id)
        if not attachment:
            flash("附件不存在", "danger")
            return redirect(url_for("main.dashboard"))

        contract = attachment.contract
        if not current_user.is_admin() and contract.user_id != current_user.id:
            flash("无权下载此附件", "danger")
            return redirect(url_for("main.dashboard"))

        directory = os.path.dirname(attachment.file_path)
        return send_from_directory(
            directory, attachment.filename,
            download_name=attachment.original_filename,
            as_attachment=True
        )

    # ---- Admin: User Management ----
    @main_bp.route("/admin/users")
    @admin_required
    def admin_users():
        users = User.query.order_by(User.created_at.desc()).all()
        return render_template("admin_users.html", users=users)

    @main_bp.route("/admin/users/<int:user_id>/toggle", methods=["POST"])
    @admin_required
    def admin_user_toggle(user_id):
        user = db.session.get(User, user_id)
        if not user:
            flash("用户不存在", "danger")
            return redirect(url_for("main.admin_users"))
        if user.id == current_user.id:
            flash("不能禁用自己", "danger")
            return redirect(url_for("main.admin_users"))
        user.is_active = not user.is_active
        db.session.commit()
        status = "启用" if user.is_active else "禁用"
        flash(f"用户 {user.username} 已{status}", "success")
        return redirect(url_for("main.admin_users"))

    @main_bp.route("/admin/users/<int:user_id>/delete", methods=["POST"])
    @admin_required
    def admin_user_delete(user_id):
        user = db.session.get(User, user_id)
        if not user:
            flash("用户不存在", "danger")
            return redirect(url_for("main.admin_users"))
        if user.id == current_user.id:
            flash("不能删除自己", "danger")
            return redirect(url_for("main.admin_users"))

        # Delete user's contract attachments from disk
        for contract in user.contracts:
            for attachment in contract.attachments:
                _delete_attachment_file(attachment)

        db.session.delete(user)
        db.session.commit()
        flash(f"用户 {user.username} 已删除", "success")
        return redirect(url_for("main.admin_users"))

    # ---- Helpers ----
    def _save_attachment(file, contract):
        """Save an uploaded file as a contract attachment."""
        ext = file.filename.rsplit(".", 1)[1].lower()
        unique_name = f"{uuid.uuid4().hex}.{ext}"
        upload_dir = app.config["UPLOAD_FOLDER"]
        file_path = os.path.join(upload_dir, unique_name)
        file.save(file_path)

        mime_map = {"pdf": "application/pdf", "doc": "application/msword",
                     "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}
        attachment = Attachment(
            filename=unique_name,
            original_filename=file.filename,
            file_path=file_path,
            file_size=os.path.getsize(file_path),
            mime_type=mime_map.get(ext, "application/octet-stream"),
            contract_id=contract.id,
        )
        db.session.add(attachment)
        db.session.commit()

    def _delete_attachment_file(attachment):
        """Remove attachment file from disk."""
        try:
            if os.path.exists(attachment.file_path):
                os.remove(attachment.file_path)
        except OSError:
            pass

    app.register_blueprint(main_bp)
    return app


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=Config.PORT, debug=True)
