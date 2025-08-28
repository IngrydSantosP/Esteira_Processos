from flask import Blueprint, jsonify
from db import get_db_connection
from datetime import datetime
from utils.notifications import notification_system

debug_bp = Blueprint("debug", __name__)

@debug_bp.route("/debug/candidatos")
def debug_candidatos():
    """Rota de debug para listar todos os candidatos"""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT id, nome, email FROM candidatos ORDER BY id")
        candidatos = cursor.fetchall()

        result = "<h2>Lista de Candidatos:</h2><ul>"
        for candidato in candidatos:
            result += f"<li>ID: {candidato[0]} - Nome: {candidato[1]} - Email: {candidato[2]}</li>"
        result += "</ul>"

        # Contar notificações por candidato
        result += "<h2>Notificações por Candidato:</h2><ul>"
        cursor.execute("""
            SELECT n.candidato_id, COUNT(*) as total, 
                   SUM(CASE WHEN n.lida = 0 THEN 1 ELSE 0 END) as nao_lidas,
                   c.nome
            FROM notificacoes n
            JOIN candidatos c ON n.candidato_id = c.id
            GROUP BY n.candidato_id, c.nome
            ORDER BY n.candidato_id
        """)

        notif_stats = cursor.fetchall()
        for stat in notif_stats:
            result += f"<li>Candidato {stat[0]} ({stat[3]}): {stat[1]} total, {stat[2]} não lidas</li>"
        result += "</ul>"

        return result

    except Exception as e:
        return f"Erro: {str(e)}"
    finally:
        conn.close()


@debug_bp.route("/debug/testar-notificacao/<int:candidato_id>")
def debug_testar_notificacao(candidato_id):
    """Rota de debug para testar notificação em candidato específico"""
    try:
        timestamp_str = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        mensagem = f"🧪 Teste de notificação para candidato {candidato_id} - {timestamp_str}"

        sucesso = notification_system.criar_notificacao(
            candidato_id, mensagem, None, None, "teste")

        return jsonify({
            "candidato_id": candidato_id,
            "sucesso": sucesso,
            "mensagem": mensagem,
            "timestamp": datetime.now().isoformat()
        })

    except Exception as e:
        return jsonify({"error": str(e), "candidato_id": candidato_id})


@debug_bp.route("/debug/notificacoes-sistema")
def debug_notificacoes_sistema_route():
    """Rota de debug para analisar sistema de notificações"""
    try:
        from utils.notifications import debug_notificacoes_sistema
        debug_notificacoes_sistema()

        conn = get_db_connection()
        cursor = conn.cursor()

        # Dados para retorno
        cursor.execute("SELECT id, nome, email FROM candidatos ORDER BY id")
        candidatos = cursor.fetchall()

        cursor.execute("""
            SELECT n.candidato_id, COUNT(*) as total, 
                   SUM(CASE WHEN n.lida = 0 THEN 1 ELSE 0 END) as nao_lidas,
                   c.nome
            FROM notificacoes n
            JOIN candidatos c ON n.candidato_id = c.id
            GROUP BY n.candidato_id, c.nome
            ORDER BY n.candidato_id
        """)

        notif_stats = cursor.fetchall()

        return jsonify({
            "status": "ok",
            "candidatos": [{
                "id": c[0],
                "nome": c[1],
                "email": c[2]
            } for c in candidatos],
            "notificacao_stats": [{
                "candidato_id": s[0],
                "total": s[1],
                "nao_lidas": s[2],
                "nome_candidato": s[3]
            } for s in notif_stats]
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


