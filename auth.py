from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from db import get_db_connection

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/login_empresa", methods=["GET", "POST"])
def login_empresa():
    if request.method == "POST":
        cnpj = request.form.get("cnpj", "").strip()
        senha = request.form.get("senha", "")

        if not cnpj or not senha:
            flash("Por favor, preencha todos os campos", "error")
            return render_template("login_empresa.html")

        cnpj_limpo = "".join(filter(str.isdigit, cnpj))

        if len(cnpj_limpo) != 14:
            flash("CNPJ deve ter exatamente 14 dígitos", "error")
            return render_template("login_empresa.html")

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                "SELECT id, senha_hash FROM empresas WHERE cnpj = ?",
                (cnpj_limpo, ))
            empresa = cursor.fetchone()

            if empresa and check_password_hash(empresa[1], senha):
                session.clear()
                session["empresa_id"] = empresa[0]
                session["tipo_usuario"] = "empresa"
                session.permanent = True
                return redirect(url_for("dashboard_empresa"))
            else:
                flash("CNPJ ou senha incorretos", "error")
        except Exception as e:
            print(f"Erro no login: {e}")
            flash("Erro interno do sistema. Tente novamente.", "error")
        finally:
            conn.close()

    return render_template("login_empresa.html")


@auth_bp.route("/cadastro_empresa", methods=["GET", "POST"])
def cadastro_empresa():
    if request.method == "POST":
        nome = request.form["nome"]
        email = request.form["email"]
        senha = request.form["senha"]
        cnpj = request.form["cnpj"]
        endereco = request.form.get("endereco", "")
        cidade = request.form.get("cidade", "")
        estado = request.form.get("estado", "")
        cep = request.form.get("cep", "")

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                """INSERT INTO empresas (nome, email, senha_hash, cnpj, endereco, cidade, estado, cep)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (nome, email, generate_password_hash(senha), cnpj, endereco,
                 cidade, estado, cep))
            conn.commit()
            flash("Empresa cadastrada com sucesso!", "success")
            return redirect(url_for("auth.login_empresa"))
        except sqlite3.IntegrityError:
            flash("Email já cadastrado", "error")
        finally:
            conn.close()

    return render_template("cadastro_empresa.html")


@auth_bp.route("/login_candidato", methods=["GET", "POST"])
@auth_bp.route("/index.html", methods=["GET", "POST"])
def login_candidato():
    if request.method == "POST":
        email = request.form["email"]
        senha = request.form["senha"]

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT id, senha_hash FROM candidatos WHERE email = ?",
                       (email, ))
        candidato = cursor.fetchone()

        if candidato and check_password_hash(candidato[1], senha):
            session["candidato_id"] = candidato[0]
            session["tipo_usuario"] = "candidato"
            return redirect(url_for("dashboard_candidato"))
        else:
            flash("Email ou senha incorretos", "error")

    return render_template("login_candidato.html")


@auth_bp.route("/cadastro_candidato", methods=["GET", "POST"])
def cadastro_candidato():
    if request.method == "POST":
        nome = request.form["nome"]
        email = request.form["email"]
        senha = request.form["senha"]
        telefone = request.form["telefone"]
        linkedin = request.form["linkedin"]
        endereco_completo = request.form["endereco_completo"]
        pretensao_salarial = float(request.form["pretensao_salarial"])

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                """INSERT INTO candidatos (nome, email, senha_hash, telefone, linkedin, endereco_completo, pretensao_salarial)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (nome, email, generate_password_hash(senha), telefone,
                 linkedin, endereco_completo, pretensao_salarial))
            conn.commit()
            flash("Candidato cadastrado com sucesso!", "success")
            return redirect(url_for("auth.login_candidato"))
        except sqlite3.IntegrityError:
            flash("Email já cadastrado", "error")
        finally:
            conn.close()

    return render_template("cadastro_candidato.html")


@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("Logout realizado com sucesso!", "success")
    return redirect(url_for("index"))


