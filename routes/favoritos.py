from flask import Blueprint, jsonify, session, request, render_template, redirect, url_for
from db import get_db_connection

favoritos_bp = Blueprint("favoritos", __name__)

# -------------------------
# API: Favoritar/desfavoritar candidato por vaga
# -------------------------
@favoritos_bp.route("/api/favoritar-candidato", methods=["POST"])
def favoritar_candidato():
    """Empresa adiciona ou remove candidato dos favoritos de uma vaga específica"""
    if "empresa_id" not in session:
        return jsonify({"success": False, "message": "Não autorizado"}), 401

    data = request.get_json()
    candidato_id = data.get("candidato_id")
    vaga_id = data.get("vaga_id")
    acao = data.get("acao", "toggle")

    if not candidato_id or not vaga_id:
        return jsonify({"success": False, "message": "Candidato ID e Vaga ID obrigatórios"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        empresa_id = session["empresa_id"]

        # Verificar se a empresa possui a vaga e candidato (através de candidatura)
        cursor.execute("""
            SELECT 1 FROM candidaturas c
            JOIN vagas v ON c.vaga_id = v.id
            WHERE c.candidato_id = %s AND c.vaga_id = %s AND v.empresa_id = %s
        """, (candidato_id, vaga_id, empresa_id))

        if not cursor.fetchone():
            return jsonify({"success": False, "message": "Candidato não encontrado nesta vaga"}), 404

        # Verificar se já está favoritado
        cursor.execute("""
            SELECT id FROM empresa_candidato_favorito
            WHERE empresa_id=%s AND candidato_id=%s AND vaga_id=%s
        """, (empresa_id, candidato_id, vaga_id))

        ja_favoritado = cursor.fetchone() is not None

        if acao == "toggle":
            if ja_favoritado:
                cursor.execute("""
                    DELETE FROM empresa_candidato_favorito
                    WHERE empresa_id=%s AND candidato_id=%s AND vaga_id=%s
                """, (empresa_id, candidato_id, vaga_id))
                conn.commit()
                return jsonify({"success": True, "favorited": False, "message": "Candidato removido dos favoritos"})
            else:
                cursor.execute("""
                    INSERT INTO empresa_candidato_favorito (empresa_id, candidato_id, vaga_id)
                    VALUES (%s, %s, %s)
                """, (empresa_id, candidato_id, vaga_id))
                conn.commit()
                return jsonify({"success": True, "favorited": True, "message": "Candidato adicionado aos favoritos"})

        elif acao == "add" and not ja_favoritado:
            cursor.execute("""
                INSERT INTO empresa_candidato_favorito (empresa_id, candidato_id, vaga_id)
                VALUES (%s, %s, %s)
            """, (empresa_id, candidato_id, vaga_id))
            conn.commit()
            return jsonify({"success": True, "favorited": True, "message": "Candidato adicionado aos favoritos"})

        elif acao == "remove" and ja_favoritado:
            cursor.execute("""
                DELETE FROM empresa_candidato_favorito
                WHERE empresa_id=%s AND candidato_id=%s AND vaga_id=%s
            """, (empresa_id, candidato_id, vaga_id))
            conn.commit()
            return jsonify({"success": True, "favorited": False, "message": "Candidato removido dos favoritos"})

        return jsonify({"success": True, "favorited": ja_favoritado, "message": "Nenhuma alteração necessária"})

    except Exception as e:
        conn.rollback()
        return jsonify({"success": False, "message": f"Erro: {str(e)}"}), 500
    finally:
        conn.close()


# -------------------------
# API: Listar favoritos da empresa (geral + por vaga)
# -------------------------
@favoritos_bp.route("/api/candidatos-favoritos")
def api_candidatos_favoritos():
    """Retorna todos os candidatos favoritos da empresa"""
    if "empresa_id" not in session:
        return jsonify({"error": "Não autorizado"}), 401

    empresa_id = session["empresa_id"]
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
         # Verifica se a tabela 'empresa_favoritoo_candidat_geral' existe
        cursor.execute("""
            SELECT COUNT(*) FROM information_schema.tables 
            WHERE table_schema = DATABASE() AND table_name = 'empresa_favorito_candidato_geral'
        """)
        exists_geral = cursor.fetchone()[0] == 0
            # Verifica se a tabela 'empresa_candidato_favorito' existe
        cursor.execute("""
            SELECT COUNT(*) FROM information_schema.tables 
            WHERE table_schema = DATABASE() AND table_name = 'empresa_candidato_favorito'
        """)
        exists_vaga = cursor.fetchone()[0] == 0 
        
        # Criar tabelas se não existirem
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS empresa_favorito_candidato_geral (
            id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
            empresa_id INT NOT NULL,
            candidato_id INT NOT NULL,
            data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY uk_empresa_candidato (empresa_id, candidato_id),
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (candidato_id) REFERENCES candidatos(id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS empresa_candidato_favorito (
            id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
            empresa_id INT NOT NULL,
            candidato_id INT NOT NULL,
            vaga_id INT NOT NULL,
            data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY uk_empresa_candidato_vaga (empresa_id, candidato_id, vaga_id),
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (candidato_id) REFERENCES candidatos(id),
            FOREIGN KEY (vaga_id) REFERENCES vagas(id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

        # Buscar favoritos gerais e por vaga
        cursor.execute("""
            SELECT c.id, c.nome, c.email, c.telefone, c.linkedin,
                   'Favorito Geral' AS vaga_titulo, 0 AS vaga_id,
                   0 AS score, 0 AS posicao,
                   efcg.data_criacao AS data_favorito
            FROM empresa_favorito_candidato_geral efcg
            JOIN candidatos c ON efcg.candidato_id = c.id
            WHERE efcg.empresa_id=%s

            UNION ALL

            SELECT c.id, c.nome, c.email, c.telefone, c.linkedin,
                   v.titulo AS vaga_titulo, v.id AS vaga_id,
                   COALESCE(ca.score,0) AS score, COALESCE(ca.posicao,0) AS posicao,
                   ecf.data_criacao AS data_favorito
            FROM empresa_candidato_favorito ecf
            JOIN candidatos c ON ecf.candidato_id = c.id
            JOIN vagas v ON ecf.vaga_id = v.id
            LEFT JOIN candidaturas ca ON ca.candidato_id=c.id AND ca.vaga_id=v.id
            WHERE ecf.empresa_id=%s
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
                "score": float(row[7]) if row[7] else 0,
                "posicao": int(row[8]) if row[8] else 0,
                "data_favorito": row[9].strftime("%Y-%m-%d %H:%M:%S") if row[9] else None
            })

        return jsonify(favoritos)

    except Exception as e:
        print(f"Erro na API candidatos-favoritos: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


# -------------------------
# Páginas de interface
# -------------------------
@favoritos_bp.route("/candidatos-geral")
def candidatos_geral():
    if "empresa_id" not in session:
        return redirect(url_for("auth.login_empresa"))
    return render_template("candidatos_geral.html")


@favoritos_bp.route("/empresa/candidatos-favoritos")
def candidatos_favoritos():
    if "empresa_id" not in session:
        return redirect(url_for("auth.login_empresa"))
    return render_template("candidatos_favoritos.html")
