from flask import Blueprint, jsonify, session, flash
from db import get_db_connection
from datetime import datetime
from utils.notifications import notification_system

notifications_bp = Blueprint("notifications", __name__)

@notifications_bp.route("/api/notificacoes")
def api_notificacoes():
    """API para buscar notificações do candidato"""
    if "candidato_id" not in session:
        return jsonify({"notificacoes": []})

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Verificar e criar colunas necessárias (executar apenas uma vez)
        cursor.execute("PRAGMA table_info(notificacoes)")
        columns = [column[1] for column in cursor.fetchall()]

        if "tipo" not in columns:
            cursor.execute("ALTER TABLE notificacoes ADD COLUMN tipo TEXT DEFAULT \"geral\"")
            conn.commit()

        if "titulo" not in columns:
            cursor.execute("ALTER TABLE notificacoes ADD COLUMN titulo TEXT DEFAULT \"\"")
            conn.commit()

        # Buscar notificações
        cursor.execute(
            """
            SELECT n.id, n.candidato_id, COALESCE(n.tipo, \"geral\") as tipo,
                   n.mensagem, COALESCE(n.lida, 0) as lida,
                   COALESCE(n.data_envio, datetime(\'now\')) as data_criacao,
                   n.vaga_id, n.empresa_id, v.titulo as vaga_titulo, e.nome as empresa_nome
            FROM notificacoes n
            LEFT JOIN vagas v ON n.vaga_id = v.id
            LEFT JOIN empresas e ON n.empresa_id = e.id
            WHERE n.candidato_id = ?
            ORDER BY n.data_envio DESC
        """, (session["candidato_id"], ))

        raw_notificacoes = cursor.fetchall()
        notificacoes = []

        emojis_tipo = {
            "contratacao": "🎉",
            "candidatura": "📝",
            "vaga_nova": "✨",
            "alteracao_vaga": "🔔",
            "vaga_congelada": "❄️",
            "vaga_excluida": "❌",
            "vaga_reativada": "🔄",
            "teste": "🧪",
            "geral": "📢"
        }

        for row in raw_notificacoes:
            try:
                data_str = row[5]
                if "T" in data_str:
                    data_criacao = datetime.fromisoformat(data_str.replace("Z", "+00:00"))
                else:
                    data_criacao = datetime.strptime(data_str, "%Y-%m-%d %H:%M:%S")
            except (ValueError, TypeError):
                data_criacao = datetime.now()

            dias_passados = (datetime.now() - data_criacao).days
            is_contratacao_recente = row[2] == "contratacao" and dias_passados <= 30

            emoji = emojis_tipo.get(row[2], "📢")
            mensagem = row[3] or ""

            # Override emoji baseado no conteúdo
            if any(palavra in mensagem.upper() for palavra in ["PARABÉNS", "CONTRATADO", "SELECIONADO"]):
                emoji = "🎉"
            elif "congelada" in mensagem.lower():
                emoji = "❄️"
            elif any(palavra in mensagem.lower() for palavra in ["excluída", "cancelada"]):
                emoji = "❌"
            elif any(palavra in mensagem.lower() for palavra in ["atualizada", "alterada"]):
                emoji = "🔔"
            elif any(palavra in mensagem.lower() for palavra in ["reativada", "retomada"]):
                emoji = "🔄"

            # Construir título da notificação
            vaga_titulo = row[8]
            empresa_nome = row[9]
            if vaga_titulo and empresa_nome:
                titulo = f"{vaga_titulo} - {empresa_nome}"
            else:
                titulo = mensagem.split("\n")[0][:50] if mensagem else "Notificação"

            notificacoes.append({
                "id": row[0],
                "tipo": row[2],
                "mensagem": mensagem,
                "data_criacao": data_criacao.strftime("%Y-%m-%d %H:%M:%S"),
                "lida": bool(row[4]),
                "emoji": emoji,
                "is_fixada": is_contratacao_recente,
                "titulo": titulo
            })

        return jsonify({"notificacoes": notificacoes, "total": len(notificacoes)})

    except Exception as e:
        print(f"Erro na API de notificações: {e}")
        return jsonify({"notificacoes": [], "error": str(e)}), 500
    finally:
        conn.close()


@notifications_bp.route("/api/notificacoes/marcar-todas", methods=["POST"])
def marcar_todas_lidas():
    """API para marcar todas as notificações como lidas"""
    if "candidato_id" not in session:
        return jsonify({"status": "erro", "mensagem": "Não autenticado"}), 401

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE notificacoes SET lida = 1 WHERE candidato_id = ?",
                   (session["candidato_id"], ))
    conn.commit()
    conn.close()

    return jsonify({"status": "ok"})


@notifications_bp.route("/api/notificacoes/marcar-lida", methods=["POST"])
def marcar_notificacao_lida():
    """API para marcar notificação individual como lida"""
    if "candidato_id" not in session:
        return jsonify({"success": False, "message": "Acesso negado"})

    data = request.get_json()
    notificacao_id = data.get("id")

    if not notificacao_id:
        return jsonify({"error": "ID da notificação é obrigatório"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE notificacoes
        SET lida = 1
        WHERE id = ? AND candidato_id = ?
    """, (notificacao_id, session["candidato_id"]))

    conn.commit()
    conn.close()

    return jsonify({"success": True})


@notifications_bp.route("/api/notificacoes/marcar-todas-lidas", methods=["PUT"])
def marcar_todas_notificacoes_lidas():
    """API para marcar todas as notificações como lidas"""
    if "candidato_id" not in session:
        return jsonify({"success": False, "message": "Acesso negado"})

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE notificacoes
        SET lida = 1
        WHERE candidato_id = ?
    """, (session["candidato_id"], ))

    conn.commit()
    conn.close()

    return jsonify({"success": True})


@notifications_bp.route("/api/notificacoes/<int:notificacao_id>/lida", methods=["PUT"])
def marcar_notificacao_individual_lida(notificacao_id):
    """API para marcar uma notificação específica como lida"""
    if "candidato_id" not in session:
        return jsonify({"success": False, "message": "Acesso negado"})

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE notificacoes
        SET lida = 1
        WHERE id = ? AND candidato_id = ?
    """, (notificacao_id, session["candidato_id"]))

    conn.commit()
    conn.close()

    return jsonify({"success": True})


@notifications_bp.route("/api/notificacoes/limpar-todas", methods=["DELETE"])
def limpar_todas_notificacoes():
    """API para limpar todas as notificações"""
    if "candidato_id" not in session:
        return jsonify({"success": False, "message": "Acesso negado"})

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM notificacoes WHERE candidato_id = ?",
                   (session["candidato_id"], ))
    conn.commit()
    conn.close()

    return jsonify({"success": True})


@notifications_bp.route("/api/notificacoes/demo", methods=["POST"])
def criar_notificacoes_demo():
    """API para criar notificações de demonstração"""
    if "candidato_id" not in session:
        return jsonify({"success": False, "message": "Acesso negado"})

    conn = get_db_connection()
    cursor = conn.cursor()

    # Criar notificações de demo
    notificacoes_demo = [
        ("🎉 Parabéns! Você foi selecionado para a vaga de Desenvolvedor Python na TechCorp!", "contratacao"),
        ("📋 Nova candidatura registrada para vaga de Data Scientist", "candidatura"),
        ("✨ Nova vaga disponível que pode interessar: Analista de Sistemas", "vaga_nova"),
        ("🔔 A vaga de Frontend Developer foi atualizada com novos requisitos", "alteracao_vaga"),
        ("❄️ A vaga de DevOps Engineer foi temporariamente congelada", "vaga_congelada"),
    ]

    for mensagem, tipo in notificacoes_demo:
        cursor.execute(
            """
            INSERT INTO notificacoes (candidato_id, mensagem, tipo, lida, data_envio)
            VALUES (?, ?, ?, 0, datetime(\'now\'))
        """, (session["candidato_id"], mensagem, tipo))

    conn.commit()
    conn.close()

    return jsonify({
        "success": True,
        "message": "Notificações de demo criadas!"
    })


@notifications_bp.route("/api/notificacoes/<int:notificacao_id>/apagar", methods=["DELETE"])
def apagar_notificacao(notificacao_id):
    """API para apagar uma notificação específica"""
    if "candidato_id" not in session:
        return jsonify({"error": "Não autorizado"}), 401

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        DELETE FROM notificacoes
        WHERE id = ? AND candidato_id = ?
    """, (notificacao_id, session["candidato_id"]))

    conn.commit()
    sucesso = cursor.rowcount > 0
    conn.close()

    return jsonify({"success": sucesso})


@notifications_bp.route("/api/notificacoes/apagar-todas", methods=["DELETE"])
def apagar_todas_notificacoes():
    """API para apagar todas as notificações"""
    if "candidato_id" not in session:
        return jsonify({"error": "Não autorizado"}), 401

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        DELETE FROM notificacoes
        WHERE candidato_id = ?
    """, (session["candidato_id"], ))

    conn.commit()
    count = cursor.rowcount
    conn.close()

    return jsonify({"success": True, "deleted_count": count})


@notifications_bp.route("/api/notificacoes/nao-lidas")
def api_notificacoes_nao_lidas():
    """API para contar notifications não lidas"""
    if "candidato_id" not in session:
        return jsonify({"count": 0})

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM notificacoes WHERE candidato_id = ? AND lida = 0",
                   (session["candidato_id"],))
    count = cursor.fetchone()[0]

    return jsonify({"count": count})


@notifications_bp.route("/debug/testar-notificacao/<int:candidato_id>")
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


@notifications_bp.route("/debug/notificacoes-sistema")
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


