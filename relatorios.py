from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from db import get_db_connection
import json
from utils.relatorio_generator import gerar_dados_graficos, gerar_relatorio_completo, gerar_html_relatorio

relatorios_bp = Blueprint("relatorios", __name__)

@relatorios_bp.route("/empresa/relatorio")
def relatorio_empresa():
    if "empresa_id" not in session:
        flash("Faça login para acessar essa página", "error")
        return redirect(url_for("auth.login_empresa"))

    empresa_id = session["empresa_id"]

    # Buscar vagas da empresa para o filtro
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, titulo FROM vagas WHERE empresa_id = ? ORDER BY titulo",
        (empresa_id, ))
    vagas_disponiveis = cursor.fetchall()
    conn.close()

    dados_graficos = gerar_dados_graficos(empresa_id)

    return render_template("relatorio_empresa.html",
                           vagas_disponiveis=vagas_disponiveis,
                           dados_graficos=json.dumps(dados_graficos))


@relatorios_bp.route("/empresa/relatorio/completo")
def relatorio_completo():
    if "empresa_id" not in session:
        return redirect(url_for("auth.login_empresa"))

    empresa_id = session["empresa_id"]
    filtro_vagas = request.args.getlist("vagas")

    # Se foi especificado filtro, converter para inteiros
    if filtro_vagas:
        try:
            filtro_vagas = [int(v) for v in filtro_vagas]
        except ValueError:
            filtro_vagas = None
    else:
        filtro_vagas = None

    try:
        dados = gerar_relatorio_completo(empresa_id, filtro_vagas)
        html_relatorio = gerar_html_relatorio(dados)

        return html_relatorio

    except Exception as e:
        flash(f"Erro ao gerar relatório: {str(e)}", "error")
        return redirect(url_for("relatorios.relatorio_empresa"))


@relatorios_bp.route("/api/relatorio/graficos")
def api_relatorio_graficos():
    if "empresa_id" not in session:
        return {"error": "Não autorizado"}, 401

    empresa_id = session["empresa_id"]
    filtro_vagas = request.args.getlist("vagas")

    if filtro_vagas:
        try:
            filtro_vagas = [int(v) for v in filtro_vagas]
        except ValueError:
            filtro_vagas = None
    else:
        filtro_vagas = None

    try:
        dados = gerar_dados_graficos(empresa_id, filtro_vagas)
        return dados
    except Exception as e:
        return {"error": str(e)}, 500


