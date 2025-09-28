from flask import Blueprint, request, jsonify, session
from db import get_db_connection
from avaliador import get_avaliador
from config import get_config

filtro_bp = Blueprint("filtro", __name__)


@filtro_bp.route("/todas-vagas")
def api_todas_vagas():
    """API para buscar todas as vagas disponíveis para o candidato"""
    if "candidato_id" not in session:
        return jsonify({"error": "Não autorizado"}), 401

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            '''
            SELECT v.id, v.titulo, v.descricao, v.requisitos, v.salario_oferecido,
                   e.nome as empresa_nome, v.diferenciais, v.tipo_vaga, v.endereco_vaga,
                   CASE WHEN cvf.id IS NOT NULL THEN 1 ELSE 0 END as is_favorita,
                   CASE WHEN ca.id IS NOT NULL THEN 1 ELSE 0 END as ja_candidatou
            FROM vagas v
            JOIN empresas e ON v.empresa_id = e.id
            LEFT JOIN candidato_vaga_favorita cvf ON cvf.candidato_id = %s AND cvf.vaga_id = v.id
            LEFT JOIN candidaturas ca ON ca.candidato_id = %s AND ca.vaga_id = v.id
            WHERE v.status = 'Ativa'
            ORDER BY v.data_criacao DESC
            ''',
            (session["candidato_id"], session["candidato_id"])
        )

        vagas_raw = cursor.fetchall()

        # Buscar informações do candidato
        cursor.execute(
            "SELECT pretensao_salarial, resumo_profissional, endereco FROM candidatos WHERE id = %s",
            (session["candidato_id"],)
        )
        candidato_info = cursor.fetchone()
        conn.close()

        if not candidato_info:
            return jsonify({"error": "Candidato não encontrado"}), 404

        # Calcular scores
        config = get_config()
        avaliador = get_avaliador(config["MODO_IA"])
        vagas_processadas = []

        for vaga in vagas_raw:
            score = avaliador.calcular_score(
                candidato_info[1], vaga[3], candidato_info[0], vaga[4],
                vaga[6] if vaga[6] else "",
                candidato_info[2] if len(candidato_info) > 2 else None,
                vaga[8], vaga[7]
            )

            vagas_processadas.append({
                "id": int(vaga[0]),
                "titulo": vaga[1],
                "descricao": vaga[2],
                "requisitos": vaga[3],
                "salario_oferecido": float(vaga[4]) if vaga[4] else 0.0,
                "empresa_nome": vaga[5],
                "diferenciais": vaga[6] or "",
                "tipo_vaga": vaga[7] or "Presencial",
                "endereco_vaga": vaga[8] or "",
                "is_favorita": bool(vaga[9]),
                "ja_candidatou": bool(vaga[10]),
                "score": float(score)
            })

        vagas_processadas.sort(key=lambda x: x["score"], reverse=True)

        return jsonify(vagas_processadas)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@filtro_bp.route("/busca-filtros")
def api_busca_filtros():
    """API para obter filtros disponíveis para busca"""
    if "candidato_id" not in session:
        return jsonify({"error": "Não autorizado"}), 401

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Categorias
        cursor.execute("SELECT id, nome FROM categorias ORDER BY nome")
        categorias = [{"id": row[0], "nome": row[1]} for row in cursor.fetchall()]

        # Localizações
        cursor.execute('''
            SELECT DISTINCT localizacao_cidade, localizacao_estado
            FROM vagas
            WHERE status = 'Ativa'
            AND (localizacao_cidade IS NOT NULL AND localizacao_cidade != '')
            ORDER BY localizacao_cidade
        ''')
        localizacoes = []
        for row in cursor.fetchall():
            if row[0] and row[1]:
                localizacoes.append(f"{row[0]}, {row[1]}")
            elif row[0]:
                localizacoes.append(row[0])

        localizacoes = list(dict.fromkeys(localizacoes))  # remover duplicatas

        return jsonify({
            "categorias": categorias,
            "localizacoes": localizacoes
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@filtro_bp.route("/buscar-vagas")
def api_buscar_vagas():
    """API para busca avançada de vagas com filtros"""
    if "candidato_id" not in session:
        return jsonify({"error": "Não autorizado"}), 401

    # parâmetros
    keyword = request.args.get("keyword", "").strip()
    location = request.args.get("location", "").strip()
    category = request.args.get("category", "").strip()
    urgency = request.args.get("urgency", "").strip()
    salary = request.args.get("salary", "").strip()
    job_type = request.args.get("type", "").strip()

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        query_base = '''
            SELECT v.id, v.titulo, v.descricao, v.requisitos, v.salario_oferecido,
                   e.nome as empresa_nome, v.diferenciais, v.tipo_vaga, v.endereco_vaga,
                   CASE WHEN cvf.id IS NOT NULL THEN 1 ELSE 0 END as is_favorita,
                   CASE WHEN ca.id IS NOT NULL THEN 1 ELSE 0 END as ja_candidatou,
                   v.urgencia_contratacao, v.localizacao_cidade, v.localizacao_estado,
                   c.nome as categoria_nome
            FROM vagas v
            JOIN empresas e ON v.empresa_id = e.id
            LEFT JOIN candidato_vaga_favorita cvf ON cvf.candidato_id = %s AND cvf.vaga_id = v.id
            LEFT JOIN candidaturas ca ON ca.candidato_id = %s AND ca.vaga_id = v.id
            LEFT JOIN categorias c ON v.categoria_id = c.id
            WHERE v.status = 'Ativa'
        '''
        params = [session["candidato_id"], session["candidato_id"]]

        if keyword:
            query_base += " AND (v.titulo LIKE %s OR v.descricao LIKE %s OR v.requisitos LIKE %s)"
            keyword_param = f"%{keyword}%"
            params.extend([keyword_param, keyword_param, keyword_param])

        if location:
            query_base += " AND (v.localizacao_cidade LIKE %s OR v.localizacao_estado LIKE %s)"
            location_param = f"%{location}%"
            params.extend([location_param, location_param])

        if category:
            query_base += " AND v.categoria_id = %s"
            params.append(category)

        if urgency:
            query_base += " AND v.urgencia_contratacao = %s"
            params.append(urgency)

        if salary:
            try:
                salary_value = float(salary)
                query_base += " AND v.salario_oferecido >= %s"
                params.append(salary_value)
            except ValueError:
                pass

        if job_type:
            query_base += " AND v.tipo_vaga = %s"
            params.append(job_type)

        query_base += " ORDER BY v.data_criacao DESC"

        cursor.execute(query_base, params)
        vagas_raw = cursor.fetchall()

        # info do candidato
        cursor.execute(
            "SELECT pretensao_salarial, resumo_profissional, endereco FROM candidatos WHERE id = %s",
            (session["candidato_id"],)
        )
        candidato_info = cursor.fetchone()

        if not candidato_info:
            return jsonify({"error": "Candidato não encontrado"}), 404

        config = get_config()
        avaliador = get_avaliador(config["MODO_IA"])
        vagas_processadas = []

        for vaga in vagas_raw:
            score = avaliador.calcular_score(
                candidato_info[1], vaga[3], candidato_info[0], vaga[4],
                vaga[6] if vaga[6] else "",
                candidato_info[2] if len(candidato_info) > 2 else None,
                vaga[8], vaga[7]
            )

            vagas_processadas.append({
                "id": int(vaga[0]),
                "titulo": vaga[1],
                "descricao": vaga[2],
                "requisitos": vaga[3],
                "salario_oferecido": float(vaga[4]) if vaga[4] else 0.0,
                "empresa_nome": vaga[5],
                "diferenciais": vaga[6] or "",
                "tipo_vaga": vaga[7] or "Presencial",
                "endereco_vaga": vaga[8] or "",
                "is_favorita": bool(vaga[9]),
                "ja_candidatou": bool(vaga[10]),
                "urgencia": vaga[11],
                "localizacao": f"{vaga[12]}, {vaga[13]}" if vaga[12] and vaga[13] else vaga[12] or "",
                "categoria": vaga[14],
                "score": float(score)
            })

        vagas_processadas.sort(key=lambda x: x["score"], reverse=True)

        return jsonify(vagas_processadas)

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()
