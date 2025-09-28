from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import check_password_hash, generate_password_hash
from db import get_db_connection
import mysql.connector

auth_bp = Blueprint("auth", __name__)

# -----------------------------
# Login Empresa
# -----------------------------
@auth_bp.route("/empresa/login", methods=["GET", "POST"])
def login_empresa():
    if request.method == "POST":
        cnpj = request.form.get("cnpj", "").strip()
        senha = request.form.get("senha", "")

        if not cnpj or not senha:
            flash("Por favor, preencha todos os campos", "error")
            return render_template("empresa/login_empresa.html")

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT id, senha_hash FROM empresas WHERE cnpj = %s", (cnpj,))
            empresa = cursor.fetchone()

            # Garante que todos os resultados foram consumidos
            cursor.fetchall()  # ou apenas garanta que não há resultados pendentes

            if empresa and check_password_hash(empresa[1], senha):
                session.clear()
                session["empresa_id"] = empresa[0]
                session["tipo_usuario"] = "empresa"
                session.permanent = True
                return redirect(url_for("vagas.dashboard_empresa"))
            else:
                flash("CNPJ ou senha incorretos", "error")
        finally:
            cursor.close()
            conn.close()




    return render_template("empresa/login_empresa.html")


# -----------------------------
# Cadastro Empresa
# -----------------------------
@auth_bp.route("/empresa/cadastro", methods=["GET", "POST"])
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
            cursor.execute("""
                INSERT INTO empresas (nome, email, senha_hash, cnpj, endereco, cidade, estado, cep)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (nome, email, generate_password_hash(senha), cnpj, endereco, cidade, estado, cep))
            conn.commit()
            flash("Empresa cadastrada com sucesso!", "success")
            return redirect(url_for("auth.login_empresa"))
        except mysql.connector.IntegrityError:
            flash("Email ou CNPJ já cadastrados", "error")
        finally:
            cursor.close()
            conn.close()

    return render_template("empresa/cadastro_empresa.html")


# -----------------------------
# Login Candidato
# -----------------------------
@auth_bp.route("/candidato/login", methods=["GET", "POST"])
@auth_bp.route("/index.html", methods=["GET", "POST"])
def login_candidato():
    if request.method == "POST":
        email = request.form["email"]
        senha = request.form["senha"]

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT id, senha_hash FROM candidatos WHERE email = %s", (email,))
        candidato = cursor.fetchone()

        if candidato and check_password_hash(candidato[1], senha):
            session["candidato_id"] = candidato[0]
            session["tipo_usuario"] = "candidato"
            return redirect(url_for("candidaturas.dashboard_candidato"))
        else:
            flash("Email ou senha incorretos", "error")

    return render_template("candidato/login_candidato.html")


# -----------------------------
# Cadastro Candidato
# -----------------------------
@auth_bp.route("/candidato/cadastro", methods=["GET", "POST"])
def cadastro_candidato():
    if request.method == "POST":
        nome = request.form["nome"]
        email = request.form["email"]
        senha = request.form["senha"]
        telefone = request.form["telefone"]
        linkedin = request.form["linkedin"]
        pretensao_salarial = float(request.form["pretensao_salarial"])

        cep = request.form["cep"]
        endereco = request.form["endereco"]
        numero = request.form["numero"]
        complemento = request.form.get("complemento", "")

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO candidatos 
                (nome, email, senha_hash, telefone, linkedin, cep, endereco, numero, complemento, pretensao_salarial)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (nome, email, generate_password_hash(senha), telefone, linkedin,
                  cep, endereco, numero, complemento, pretensao_salarial))
            conn.commit()
            flash("Candidato cadastrado com sucesso!", "success")
            return redirect(url_for("auth.login_candidato"))
        except mysql.connector.IntegrityError:
            flash("Email já cadastrado", "error")
        finally:
            conn.close()

    return render_template("candidato/cadastro_candidato.html")
