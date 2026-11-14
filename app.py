import os
from functools import wraps
from datetime import datetime

from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)

database_url = os.environ.get("DATABASE_URL", "sqlite:///bottask.db")
# O Render pode fornecer a URL antiga com postgres://; SQLAlchemy espera postgresql://.
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config.update(
    SECRET_KEY=os.environ.get("SECRET_KEY", "chave-local-apenas-para-desenvolvimento"),
    SQLALCHEMY_DATABASE_URI=database_url,
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    SQLALCHEMY_ENGINE_OPTIONS={"pool_pre_ping": True},
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=bool(os.environ.get("RENDER")),
)

db = SQLAlchemy(app)
csrf = CSRFProtect(app)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(30), nullable=False)
    email = db.Column(db.String(254), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    xp = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    tasks = db.relationship("Task", backref="owner", lazy=True, cascade="all, delete-orphan")


class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    completed = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if not session.get("user_id"):
            flash("Entre na sua conta para continuar.", "info")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped_view


def get_logged_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    return db.session.get(User, user_id)


@app.route("/")
@login_required
def inicio():
    user = get_logged_user()
    if user is None:
        session.clear()
        return redirect(url_for("login"))

    tarefas = (
        Task.query.filter_by(user_id=user.id)
        .order_by(Task.created_at.desc())
        .all()
    )
    return render_template(
        "index.html",
        user=user,
        tarefas=tarefas,
        nivel=user.xp // 100,
        progresso=user.xp % 100,
    )


@app.route("/cadastro", methods=["GET", "POST"])
def cadastro():
    if session.get("user_id"):
        return redirect(url_for("inicio"))

    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        email = request.form.get("email", "").strip().lower()
        senha = request.form.get("senha", "")

        if not nome or not email or not senha:
            flash("Preencha todos os campos.", "error")
        elif len(nome) > 30:
            flash("O nome deve ter no máximo 30 caracteres.", "error")
        elif "@" not in email or len(email) > 254:
            flash("Digite um e-mail válido.", "error")
        elif len(senha) < 8:
            flash("A senha precisa ter pelo menos 8 caracteres.", "error")
        elif User.query.filter_by(email=email).first():
            flash("Este e-mail já está cadastrado. Faça login.", "error")
        else:
            user = User(
                name=nome,
                email=email,
                password_hash=generate_password_hash(senha),
            )
            db.session.add(user)
            db.session.commit()
            session.clear()
            session["user_id"] = user.id
            session["user_name"] = user.name
            flash("Conta criada! Bem-vindo ao BotTask.", "success")
            return redirect(url_for("inicio"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("inicio"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        senha = request.form.get("senha", "")
        user = User.query.filter_by(email=email).first()

        if user is None or not check_password_hash(user.password_hash, senha):
            flash("E-mail ou senha incorretos.", "error")
        else:
            session.clear()
            session["user_id"] = user.id
            session["user_name"] = user.name
            flash("Login realizado com sucesso!", "success")
            return redirect(url_for("inicio"))

    return render_template("login.html")


@app.route("/logout", methods=["POST"])
@login_required
def logout():
    session.clear()
    flash("Você saiu da sua conta.", "info")
    return redirect(url_for("login"))


@app.route("/adicionar", methods=["POST"])
@login_required
def adicionar():
    nome_tarefa = request.form.get("tarefa", "").strip()
    user = get_logged_user()

    if not nome_tarefa:
        flash("Digite o nome da missão.", "error")
    elif len(nome_tarefa) > 120:
        flash("A missão deve ter no máximo 120 caracteres.", "error")
    else:
        db.session.add(Task(name=nome_tarefa, user_id=user.id))
        db.session.commit()
        flash("Missão adicionada!", "success")

    return redirect(url_for("inicio"))


@app.route("/concluir/<int:task_id>", methods=["POST"])
@login_required
def concluir(task_id):
    user = get_logged_user()
    tarefa = Task.query.filter_by(id=task_id, user_id=user.id).first_or_404()

    if not tarefa.completed:
        tarefa.completed = True
        user.xp += 20
        db.session.commit()
        flash("Missão concluída! Você ganhou 20 XP.", "success")

    return redirect(url_for("inicio"))


# Cria as tabelas na primeira inicialização. Para projetos maiores, use migrações.
with app.app_context():
    db.create_all()


if __name__ == "__main__":
    app.run(debug=True)
