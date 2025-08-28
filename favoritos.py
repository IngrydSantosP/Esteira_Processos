from flask import Blueprint, jsonify, session
from db import get_db_connection

favoritos_bp = Blueprint("favoritos", __name__)

@favoritos_bp.route("/api/favoritar-candidato", methods=["POST"])
def favoritar_candidato():
    """API para empresa favoritar/desfavoritar candidato"""
    if "empresa_id" not in session:
        return jsonify({"success": False, "message": "Não autorizado"}), 401

    data = request.get_json()
    candidato_id = data.get("candidato_id")
    vaga_id = data.get("vaga_id")
    acao = data.get("acao", "toggle")

    if not candidato_id or not vaga_id:
        return jsonify({
            "success": False,
            "message": "Candidato ID e Vaga ID obrigatórios"
        }), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        empresa_id = session["empresa_id"]

        # Verificar se a empresa tem acesso ao candidato (através de candidatura)
        cursor.execute(
            """
            SELECT c.vaga_id FROM candidaturas c
            JOIN vagas v ON c.vaga_id = v.id
            WHERE c.candidato_id = ? AND v.empresa_id = ? AND c.vaga_id = ?
        """, (candidato_id, empresa_id, vaga_id))

        if not cursor.fetchone():
            return jsonify({
                "success": False,
                "message": "Candidato não encontrado nesta vaga"
            }), 404

        # Verificar se já está favoritado
        cursor.execute(
            """
            SELECT id FROM empresa_candidato_favorito
            WHERE empresa_id = ? AND candidato_id = ? AND vaga_id = ?
        """, (empresa_id, candidato_id, vaga_id))

        ja_favoritado = cursor.fetchone() is not None

        if acao == "toggle" or (acao == "add" and not ja_favoritado):
            if ja_favoritado:
                # Remover dos favoritos
                cursor.execute(
                    """
                    DELETE FROM empresa_candidato_favorito
                    WHERE empresa_id = ? AND candidato_id = ? AND vaga_id = ?
                """, (empresa_id, candidato_id, vaga_id))
                conn.commit()
                return jsonify({
                    "success": True,
                    "favorited": False,
                    "message": "Candidato removido dos favoritos"
                })
            else:
                # Adicionar aos favoritos
                cursor.execute(
                    """
                    INSERT INTO empresa_candidato_favorito (empresa_id, candidato_id, vaga_id)
                    VALUES (?, ?, ?)
                """, (empresa_id, candidato_id, vaga_id))
                conn.commit()
                return jsonify({
                    "success": True,
                    "favorited": True,
                    "message": "Candidato adicionado aos favoritos"
                })

        elif acao == "remove" and ja_favoritado:
            cursor.execute(
                """
                DELETE FROM empresa_candidato_favorito
                WHERE empresa_id = ? AND candidato_id = ? AND vaga_id = ?
            """, (empresa_id, candidato_id, vaga_id))
            conn.commit()
            return jsonify({
                "success": True,
                "favorited": False,
                "message": "Candidato removido dos favoritos"
            })

        return jsonify({
            "success": True,
            "favorited": ja_favoritado,
            "message": "Nenhuma alteração necessária"
        })

    except Exception as e:
        conn.rollback()
        return jsonify({"success": False, "message": f"Erro: {str(e)}"}), 500
    finally:
        conn.close()


@favoritos_bp.route("/api/candidatos-favoritos")
def api_candidatos_favoritos():
    """API para listar candidatos favoritos da empresa"""
    if "empresa_id" not in session:
        return jsonify({"error": "Não autorizado"}), 401

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Garantir que as tabelas existem
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS empresa_favorito_candidato_geral (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                empresa_id INTEGER NOT NULL,
                candidato_id INTEGER NOT NULL,
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (empresa_id) REFERENCES empresas (id),
                FOREIGN KEY (candidato_id) REFERENCES candidatos (id),
                UNIQUE(empresa_id, candidato_id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS empresa_candidato_favorito (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                empresa_id INTEGER,
                candidato_id INTEGER,
                vaga_id INTEGER,
                data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (empresa_id) REFERENCES empresas (id),
                FOREIGN KEY (candidato_id) REFERENCES candidatos (id),
                FOREIGN KEY (vaga_id) REFERENCES vagas (id),
                UNIQUE(empresa_id, candidato_id, vaga_id)
            )
        """)

        empresa_id = session["empresa_id"]

        # Buscar candidatos favoritos gerais
        cursor.execute(
            """
            SELECT DISTINCT c.id, c.nome, c.email, c.telefone, c.linkedin,
                   'Favorito Geral' as vaga_titulo, 0 as vaga_id,
                   0 as score, 0 as posicao,
                   efcg.data_criacao as data_favorito
            FROM empresa_favorito_candidato_geral efcg
            JOIN candidatos c ON efcg.candidato_id = c.id
            WHERE efcg.empresa_id = ?

            UNION

            SELECT DISTINCT c.id, c.nome, c.email, c.telefone, c.linkedin,
                   v.titulo as vaga_titulo, v.id as vaga_id,
                   COALESCE(ca.score, 0) as score, COALESCE(ca.posicao, 0) as posicao,
                   ecf.data_criacao as data_favorito
            FROM empresa_candidato_favorito ecf
            JOIN candidatos c ON ecf.candidato_id = c.id
            JOIN vagas v ON ecf.vaga_id = v.id
            LEFT JOIN candidaturas ca ON ca.candidato_id = c.id AND ca.vaga_id = v.id
            WHERE ecf.empresa_id = ?

            ORDER BY data_favorito DESC
        """, (empresa_id, empresa_id))

        favoritos = []
        for row in cursor.fetchall():
            favoritos.append({
                "id": row[0],
                "nome": row[1],
                "email": row[2],
                "telefone": row[3],
                "linkedin": row[4],
                "vaga_titulo": row[5],
                "vaga_id": row[6],
                "score": round(row[7], 1) if row[7] else 0,
                "posicao": row[8] if row[8] else 0,
                "data_favorito": row[9]
            })

        return jsonify(favoritos)

    except Exception as e:
        print(f"Erro na API candidatos-favoritos: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@favoritos_bp.route("/candidatos-geral")
def candidatos_geral():
    """Página para visualizar todos os candidatos cadastrados"""
    if "empresa_id" not in session:
        return redirect(url_for("auth.login_empresa"))

    return render_template("candidatos_geral.html")


@favoritos_bp.route("/api/candidatos-geral")
def api_candidatos_geral():
    """API para listar todos os candidatos cadastrados"""
    if "empresa_id" not in session:
        return jsonify({"error": "Não autorizado"}), 401

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Primeiro, verificar se a tabela de favoritos existe e criá-la se necessário
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS empresa_favorito_candidato_geral (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                empresa_id INTEGER NOT NULL,
                candidato_id INTEGER NOT NULL,
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (empresa_id) REFERENCES empresas (id),
                FOREIGN KEY (candidato_id) REFERENCES candidatos (id),
                UNIQUE(empresa_id, candidato_id)
            )
        """)

        # Verificar se a coluna data_cadastro existe e criá-la se necessário
        cursor.execute("PRAGMA table_info(candidatos)")
        columns = [column[1] for column in cursor.fetchall()]

        if "data_cadastro" not in columns:
            cursor.execute(
                "ALTER TABLE candidatos ADD COLUMN data_cadastro TIMESTAMP")
            # Atualizar registros existentes com data atual
            cursor.execute(
                "UPDATE candidatos SET data_cadastro = datetime(\"now\") WHERE data_cadastro IS NULL"
            )

        empresa_id = session["empresa_id"]

        cursor.execute(
            """
            SELECT DISTINCT c.id, c.nome, c.email, c.telefone, c.linkedin,
                   c.endereco, c.pretensao_salarial, c.competencias,
                   c.resumo_profissional, COALESCE(c.data_cadastro, datetime("now")) as data_cadastro,
                   CASE WHEN c.resumo_profissional IS NOT NULL AND c.resumo_profissional != '' THEN 1 ELSE 0 END as tem_curriculo,
                   CASE WHEN efcg.candidato_id IS NOT NULL THEN 1 ELSE 0 END as is_favorito
            FROM candidatos c
            LEFT JOIN empresa_favorito_candidato_geral efcg ON efcg.candidato_id = c.id AND efcg.empresa_id = ?
            ORDER BY COALESCE(c.data_cadastro, datetime("now")) DESC
        """, (empresa_id, ))

        candidatos = []
        for row in cursor.fetchall():
            candidatos.append({
                "id": row[0],
                "nome": row[1] or "",
                "email": row[2] or "",
                "telefone": row[3] or "",
                "linkedin": row[4] or "",
                "endereco": row[5] or "",
                "pretensao_salarial": row[6] or 0,
                "competencias": row[7] or "",
                "resumo_profissional": row[8] or "",
                "data_cadastro": row[9] or "",
                "tem_curriculo": bool(row[10]),
                "is_favorito": bool(row[11])
            })

        return jsonify(candidatos)

    except Exception as e:
        print(f"Erro na API candidatos-geral: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@favoritos_bp.route("/api/favoritar-candidato-geral", methods=["POST"])
def favoritar_candidato_geral():
    """API para empresa favoritar/desfavoritar candidato geral"""
    if "empresa_id" not in session:
        return jsonify({"success": False, "message": "Não autorizado"}), 401

    data = request.get_json()
    candidato_id = data.get("candidato_id")
    acao = data.get("acao", "toggle")

    if not candidato_id:
        return jsonify({
            "success": False,
            "message": "Candidato ID obrigatório"
        }), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Garantir que a tabela existe
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS empresa_favorito_candidato_geral (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                empresa_id INTEGER NOT NULL,
                candidato_id INTEGER NOT NULL,
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (empresa_id) REFERENCES empresas (id),
                FOREIGN KEY (candidato_id) REFERENCES candidatos (id),
                UNIQUE(empresa_id, candidato_id)
            )
        """)

        empresa_id = session["empresa_id"]

        # Verificar se o candidato existe
        cursor.execute("SELECT id FROM candidatos WHERE id = ?",
                       (candidato_id, ))
        if not cursor.fetchone():
            return jsonify({
                "success": False,
                "message": "Candidato não encontrado"
            }), 404

        # Verificar se já está favoritado
        cursor.execute(
            """
            SELECT id FROM empresa_favorito_candidato_geral
            WHERE empresa_id = ? AND candidato_id = ?
        """, (empresa_id, candidato_id))

        ja_favoritado = cursor.fetchone() is not None

        if acao == "toggle" or (acao == "add" and not ja_favoritado):
            if ja_favoritado:
                # Remover dos favoritos
                cursor.execute(
                    """
                    DELETE FROM empresa_favorito_candidato_geral
                    WHERE empresa_id = ? AND candidato_id = ?
                """, (empresa_id, candidato_id))
                conn.commit()
                return jsonify({
                    "success": True,
                    "favorited": False,
                    "message": "Candidato removido dos favoritos"
                })
            else:
                # Adicionar aos favoritos
                cursor.execute(
                    """
                    INSERT INTO empresa_favorito_candidato_geral (empresa_id, candidato_id)
                    VALUES (?, ?)
                """, (empresa_id, candidato_id))
                conn.commit()
                return jsonify({
                    "success": True,
                    "favorited": True,
                    "message": "Candidato adicionado aos favoritos"
                })

        elif acao == "remove" and ja_favoritado:
            cursor.execute(
                """
                DELETE FROM empresa_favorito_candidato_geral
                WHERE empresa_id = ? AND candidato_id = ?
            """, (empresa_id, candidato_id))
            conn.commit()
            return jsonify({
                "success": True,
                "favorited": False,
                "message": "Candidato removido dos favoritos"
            })

        return jsonify({
            "success": True,
            "favorited": ja_favoritado,
            "message": "Nenhuma alteração necessária"
        })

    except Exception as e:
        conn.rollback()
        print(f"Erro ao favoritar candidato geral: {e}")
        return jsonify({"success": False, "message": f"Erro: {str(e)}"}), 500
    finally:
        conn.close()


@favoritos_bp.route("/empresa/candidatos-favoritos")
def candidatos_favoritos():
    """Página para visualizar candidatos favoritos"""
    if "empresa_id" not in session:
        return redirect(url_for("auth.login_empresa"))

    return render_template("candidatos_favoritos.html")


@favoritos_bp.route("/api/favoritos/toggle", methods=["POST"])
def api_toggle_favorito():
    """API para adicionar/remover vaga dos favoritos"""
    if "candidato_id" not in session:
        return jsonify({"error": "Não autorizado", "favorited": False}), 401

    data = request.get_json()
    if not data or "vaga_id" not in data:
        return jsonify({"error": "ID da vaga é obrigatório", "favorited": False}), 400

    candidato_id = session["candidato_id"]
    vaga_id = data["vaga_id"]

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Verificar se já existe nos favoritos
        cursor.execute(
            "SELECT id FROM candidato_vaga_favorita WHERE candidato_id = ? AND vaga_id = ?",
            (candidato_id, vaga_id)
        )
        favorito_existente = cursor.fetchone()

        if favorito_existente:
            # Remover dos favoritos
            cursor.execute(
                "DELETE FROM candidato_vaga_favorita WHERE candidato_id = ? AND vaga_id = ?",
                (candidato_id, vaga_id)
            )
            favorited = False
            action = "removida"
        else:
            # Adicionar aos favoritos
            cursor.execute(
                "INSERT INTO candidato_vaga_favorita (candidato_id, vaga_id, data_adicao) VALUES (?, ?, datetime(\"now\"))",
                (candidato_id, vaga_id)
            )
            favorited = True
            action = "adicionada"

        conn.commit()
        return jsonify({
            "success": True,
            "favorited": favorited,
            "message": f"Vaga {action} dos favoritos com sucesso!"
        })

    except Exception as e:
        conn.rollback()
        return jsonify({
            "error": f"Erro ao atualizar favoritos: {str(e)}",
            "favorited": False
        }), 500
    finally:
        conn.close()


