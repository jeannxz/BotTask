
from flask import Flask, render_template, request, redirect, session
from datetime import timedelta

app = Flask(__name__)

app.secret_key = "bottask_chave_secreta"
app.permanent_session_lifetime = timedelta(days=30)

xp = 0
tarefas = []

@app.route("/")
def inicio():
    nome = session.get("nome", "Aventureiro")
    nivel = xp // 100

    return render_template(
        "index.html",
        xp=xp,
        nivel=nivel,
        tarefas=tarefas,
        nome=nome
    )

@app.route("/salvar_nome", methods=["POST"])
def salvar_nome():
    nome = request.form.get("nome", "").strip()

    if nome:
        session.permanent = True
        session["nome"] = nome[:30]

    return redirect("/")

@app.route("/adicionar", methods=["POST"])
def adicionar():
    tarefa = request.form.get("tarefa")

    if tarefa:
        tarefas.append({
            "nome": tarefa,
            "concluida": False
        })

    return redirect("/")

@app.route("/concluir/<int:id>")
def concluir(id):
    global xp

    if 0 <= id < len(tarefas):
        if not tarefas[id]["concluida"]:
            tarefas[id]["concluida"] = True
            xp += 20

    return redirect("/")

if __name__ == "__main__":
    app.run(debug=True)
