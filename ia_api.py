from flask import Blueprint, jsonify, session
from db import get_db_connection
from ia_utils import get_ia_assistant
from utils.notifications import notification_system

ia_api_bp = Blueprint("ia_api", __name__)

@ia_api_bp.route("/api/ia/analise-curriculo/<int:candidato_id>")
def api_analise_curriculo(candidato_id):
    """API para análise de currículo com IA"""
    if "candidato_id" not in session:
        return jsonify({"error": "Não autorizado"}), 401

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Verificar se o candidato logado é o mesmo que está sendo analisado
        if candidato_id != session["candidato_id"]:
            return jsonify({"error": "Acesso negado para este currículo"}), 403

        cursor.execute("SELECT texto_curriculo FROM candidatos WHERE id = ?",
                       (candidato_id, ))
        resultado = cursor.fetchone()

        if not resultado or not resultado[0]:
            return jsonify({"error": "Currículo não encontrado"}), 404

        curriculo_texto = resultado[0]

        # Analisar currículo com IA
        analise = get_ia_assistant().analisar_curriculo(candidato_id,
                                                         curriculo_texto)

        return jsonify(analise)

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@ia_api_bp.route("/api/ia/recomendacoes-vagas")
def api_recomendacoes_ia():
    """API para recomendações personalizadas de vagas"""
    if "candidato_id" not in session:
        return jsonify({"error": "Não autorizado"}), 401

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        candidato_id = session["candidato_id"]

        # Buscar currículo do candidato
        cursor.execute("SELECT texto_curriculo FROM candidatos WHERE id = ?",
                       (candidato_id, ))
        resultado = cursor.fetchone()

        if not resultado or not resultado[0]:
            return jsonify({"error": "Currículo não encontrado"}), 404

        curriculo_texto = resultado[0]

        # Obter recomendações da IA
        recomendacoes = get_ia_assistant().recomendar_vagas_personalizadas(
            candidato_id, curriculo_texto)

        return jsonify(recomendacoes)

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@ia_api_bp.route("/api/ia/dicas-vaga/<int:vaga_id>")
def api_dicas_vaga_ia(vaga_id):
    """API para dicas específicas de uma vaga"""
    if "candidato_id" not in session:
        return jsonify({"error": "Não autorizado"}), 401

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        candidato_id = session["candidato_id"]

        # Buscar dados do candidato e da vaga
        cursor.execute(
            """
            SELECT c.texto_curriculo, v.requisitos, v.salario_oferecido
            FROM candidatos c, vagas v
            WHERE c.id = ? AND v.id = ? AND v.status = 'Ativa'
        """, (candidato_id, vaga_id))

        resultado = cursor.fetchone()

        if not resultado:
            return jsonify({"error": "Dados não encontrados"}), 404

        curriculo_texto, requisitos_vaga, salario_vaga = resultado

        # Gerar dicas da IA
        dicas = get_ia_assistant().gerar_dicas_melhoria_vaga(curriculo_texto,
                                                       requisitos_vaga,
                                                       salario_vaga)

        return jsonify(dicas)

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@ia_api_bp.route("/api/ia/enviar-recomendacoes", methods=["POST"])
def api_enviar_recomendacoes_email():
    """API para enviar recomendações por email"""
    if "candidato_id" not in session:
        return jsonify({"error": "Não autorizado"}), 401

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        candidato_id = session["candidato_id"]

        # Buscar dados do candidato
        cursor.execute(
            "SELECT nome, email, texto_curriculo FROM candidatos WHERE id = ?",
            (candidato_id, ))
        resultado = cursor.fetchone()

        if not resultado:
            return jsonify({"error": "Candidato não encontrado"}), 404

        candidato_nome, candidato_email, curriculo_texto = resultado

        # Obter análise e recomendações
        analise = get_ia_assistant().analisar_curriculo(candidato_id,
                                                         curriculo_texto)
        recomendacoes = get_ia_assistant().recomendar_vagas_personalizadas(
            candidato_id, curriculo_texto)

        # Gerar dicas gerais
        dicas = []
        if analise["areas_melhoria"]:
            for area in analise["areas_melhoria"][:3]:
                dicas.append({
                    "titulo": f"Melhore: {area}",
                    "descricao":
                    f"Considere desenvolver mais esta área do seu perfil",
                    "prioridade": "media",
                    "icone": "💡"
                })

        # Dados para o template
        template_data = {
            "candidato_nome": candidato_nome,
            "analise": analise,
            "recomendacoes": recomendacoes,
            "dicas": dicas
        }

        # Enviar email com template da IA
        assunto = "🤖 Recomendações Personalizadas da IA"
        sucesso = notification_system.enviar_email(
            candidato_email, assunto,
            "Suas recomendações personalizadas estão prontas!", template_data,
            "recomendacao_ia")

        if sucesso:
            return jsonify({
                "success": True,
                "message": "Recomendações enviadas por email!"
            })
        else:
            return jsonify({
                "success": False,
                "message": "Erro ao enviar email"
            }), 500

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


