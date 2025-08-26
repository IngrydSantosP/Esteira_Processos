from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, send_file
from db import get_db_connection
from config import get_config
from avaliador import criar_avaliador
from utils.resume_extractor import processar_upload_curriculo, finalizar_processamento_curriculo
from utils.helpers import processar_candidatura
import os

candidaturas_bp = Blueprint("candidaturas", __name__)

@candidaturas_bp.route("/candidatos_vaga/<int:vaga_id>")
def candidatos_vaga(vaga_id):
    if "empresa_id" not in session:
        return redirect(url_for("auth.login_empresa"))

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """SELECT c.nome, c.email, c.telefone, c.linkedin, ca.score, ca.posicao, c.id, c.endereco_completo
           FROM candidaturas ca
           JOIN candidatos c ON ca.candidato_id = c.id
           WHERE ca.vaga_id = ?
           ORDER BY ca.score DESC""", (vaga_id, ))

    candidatos = cursor.fetchall()

    cursor.execute("SELECT titulo FROM vagas WHERE id = ?", (vaga_id, ))
    vaga = cursor.fetchone()
    conn.close()

    return render_template("candidatos_vaga.html",
                           candidatos=candidatos,
                           vaga_titulo=vaga[0] if vaga else "",
                           vaga_id=vaga_id)


@candidaturas_bp.route("/dashboard_candidato")
def dashboard_candidato():
    if "candidato_id" not in session:
        return redirect(url_for("auth.login_candidato"))

    conn = get_db_connection()
    cursor = conn.cursor()

    # Verifica se o candidato já enviou currículo
    cursor.execute("SELECT texto_curriculo FROM candidatos WHERE id = ?",
                   (session["candidato_id"], ))
    candidato = cursor.fetchone()

    if not candidato or not candidato[0]:
        conn.close()
        return redirect(url_for("candidaturas.upload_curriculo"))

    # Candidaturas em vagas ATIVAS, ordenadas por score decrescente
    cursor.execute(
        """
        SELECT v.id, v.titulo, e.nome AS empresa_nome, v.salario_oferecido, ca.score, ca.posicao,
               CASE WHEN cvf.id IS NOT NULL THEN 1 ELSE 0 END as is_favorita
        FROM candidaturas ca
        JOIN vagas v ON ca.vaga_id = v.id
        JOIN empresas e ON v.empresa_id = e.id
        LEFT JOIN candidato_vaga_favorita cvf ON cvf.candidato_id = ? AND cvf.vaga_id = v.id
        WHERE ca.candidato_id = ? AND v.status = 'Ativa'
        ORDER BY ca.score DESC
        """, (session["candidato_id"], session["candidato_id"]))
    vagas_candidatadas_raw = cursor.fetchall()

    # Processamento dos dados
    vagas_candidatadas = []
    for vaga in vagas_candidatadas_raw:
        vaga_processada = (
            int(vaga[0]),  # id
            vaga[1],  # titulo
            vaga[2],  # empresa_nome
            float(vaga[3]) if vaga[3] else 0.0,  # salario
            float(vaga[4]) if vaga[4] else 0.0,  # score
            int(vaga[5]) if vaga[5] else 0,  # posicao
            bool(vaga[6])  # is_favorita
        )
        vagas_candidatadas.append(vaga_processada)

    # Agora busca vagas disponíveis que o candidato ainda não se candidatou
    cursor.execute(
        """
        SELECT v.id, v.titulo, v.descricao, v.requisitos, v.salario_oferecido,
               e.nome as empresa_nome, v.diferenciais, v.tipo_vaga, v.endereco_vaga,
               CASE WHEN cvf.id IS NOT NULL THEN 1 ELSE 0 END as is_favorita
        FROM vagas v
        JOIN empresas e ON v.empresa_id = e.id
        LEFT JOIN candidato_vaga_favorita cvf ON cvf.candidato_id = ? AND cvf.vaga_id = v.id
        WHERE v.id NOT IN (
            SELECT vaga_id FROM candidaturas WHERE candidato_id = ?
        ) AND v.status = 'Ativa'
        """, (session["candidato_id"], session["candidato_id"]))
    vagas_disponiveis = cursor.fetchall()

    # Buscar vagas favoritas (com e sem candidatura)
    cursor.execute(
        """
        SELECT v.id, v.titulo, v.descricao, v.requisitos, v.salario_oferecido,
               e.nome as empresa_nome, v.diferenciais, v.tipo_vaga, v.endereco_vaga,
               CASE WHEN ca.id IS NOT NULL THEN 1 ELSE 0 END as ja_candidatou,
               ca.score, ca.posicao
        FROM candidato_vaga_favorita cvf
        JOIN vagas v ON cvf.vaga_id = v.id
        JOIN empresas e ON v.empresa_id = e.id
        LEFT JOIN candidaturas ca ON ca.candidato_id = ? AND ca.vaga_id = v.id
        WHERE cvf.candidato_id = ? AND v.status = 'Ativa'
        ORDER BY cvf.data_criacao DESC
        """, (session["candidato_id"], session["candidato_id"]))
    vagas_favoritas = cursor.fetchall()

    # Informações do candidato
    cursor.execute(
        "SELECT pretensao_salarial, texto_curriculo, endereco_completo FROM candidatos WHERE id = ?",
        (session["candidato_id"], ))
    candidato_info = cursor.fetchone()

    conn.close()

    # Calcula score para vagas disponíveis
    config = get_config()
    avaliador = criar_avaliador(config["MODO_IA"])
    vagas_com_score = []
    for vaga in vagas_disponiveis:
        score = avaliador.calcular_score(
            candidato_info[1], vaga[3], candidato_info[0], vaga[4],
            vaga[6] if vaga[6] else "",
            candidato_info[2] if len(candidato_info) > 2 else None, vaga[8],
            vaga[7])
        vaga_processada = (int(vaga[0]), vaga[1], vaga[2], vaga[3],
                           float(vaga[4]) if vaga[4] else 0.0, vaga[5], vaga[6]
                           or "", vaga[7] or "Presencial", vaga[8]
                           or "", float(score), bool(vaga[9]))
        vagas_com_score.append(vaga_processada)

    # Processa vagas favoritas
    vagas_favoritas_processadas = []
    for vaga in vagas_favoritas:
        if not vaga[9]:  # Se não se candidatou ainda, calcular score
            score = avaliador.calcular_score(
                candidato_info[1], vaga[3], candidato_info[0], vaga[4],
                vaga[6] if vaga[6] else "",
                candidato_info[2] if len(candidato_info) > 2 else None,
                vaga[8], vaga[7])
        else:
            score = vaga[10]  # Score já existente da candidatura

        vaga_processada = {
            "id": int(vaga[0]),
            "titulo": vaga[1],
            "descricao": vaga[2],
            "requisitos": vaga[3],
            "salario": float(vaga[4]) if vaga[4] else 0.0,
            "empresa_nome": vaga[5],
            "diferenciais": vaga[6] or "",
            "tipo_vaga": vaga[7] or "Presencial",
            "endereco_vaga": vaga[8] or "",
            "ja_candidatou": bool(vaga[9]),
            "score": float(score) if score else 0.0,
            "posicao": int(vaga[11]) if vaga[11] else None,
            "is_favorita": True
        }
        vagas_favoritas_processadas.append(vaga_processada)

    # Ordena pelas melhores recomendações
    vagas_com_score.sort(key=lambda x: x[9], reverse=True)
    top_vagas = vagas_com_score[:config["TOP_JOBS"]]

    return render_template("dashboard_candidato.html",
                           vagas_recomendadas=top_vagas,
                           vagas_candidatadas=vagas_candidatadas,
                           vagas_favoritas=vagas_favoritas_processadas)


@candidaturas_bp.route("/upload_curriculo", methods=["GET", "POST"])
def upload_curriculo():
    if "candidato_id" not in session:
        return redirect(url_for("auth.login_candidato"))

    if request.method == "POST":
        resultado = processar_upload_curriculo(request,
                                               session["candidato_id"])

        # Processar mensagens corretamente
        for mensagem in resultado["mensagens"]:
            if isinstance(mensagem, dict) and "texto" in mensagem:
                flash(mensagem["texto"], mensagem.get("tipo", "info"))
            else:
                flash(str(mensagem), "info")

        if resultado["sucesso"]:
            return render_template(
                "processar_curriculo.html",
                dados_extraidos=resultado["dados_extraidos"])
        else:
            return redirect(request.url)

    return render_template("upload_curriculo.html")


@candidaturas_bp.route("/finalizar_curriculo", methods=["POST"])
def finalizar_curriculo():
    if "candidato_id" not in session:
        return redirect(url_for("auth.login_candidato"))

    resultado = finalizar_processamento_curriculo(request,
                                                  session["candidato_id"])

    # Processar mensagens corretamente
    for mensagem in resultado["mensagens"]:
        if isinstance(mensagem, dict) and "texto" in mensagem:
            flash(mensagem["texto"], mensagem.get("tipo", "info"))
        else:
            flash(str(mensagem), "info")

    if resultado["sucesso"]:
        return redirect(url_for("candidaturas.dashboard_candidato"))
    else:
        return redirect(url_for("candidaturas.upload_curriculo"))


@candidaturas_bp.route("/candidatar/<int:vaga_id>")
def candidatar(vaga_id):
    if "candidato_id" not in session:
        return redirect(url_for("auth.login_candidato"))

    config = get_config()
    resultado = processar_candidatura(session["candidato_id"], vaga_id,
                                      config["MODO_IA"])

    # Processar mensagens para garantir que estão em formato correto
    for mensagem in resultado["mensagens"]:
        if isinstance(mensagem, dict) and "texto" in mensagem:
            flash(mensagem["texto"], mensagem.get("tipo", "info"))
        else:
            flash(str(mensagem), "info")

    return redirect(url_for("candidaturas.dashboard_candidato"))


@candidaturas_bp.route("/minhas_candidaturas")
def minhas_candidaturas():
    if "candidato_id" not in session:
        return redirect(url_for("auth.login_candidato"))

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT v.id, v.titulo, e.nome as empresa_nome, v.salario_oferecido,
               ca.score, ca.posicao, ca.data_candidatura,
               DATE(ca.data_candidatura) as data_formatada
        FROM candidaturas ca
        JOIN vagas v ON ca.vaga_id = v.id
        JOIN empresas e ON v.empresa_id = e.id
        WHERE ca.candidato_id = ?
        ORDER BY ca.data_candidatura DESC
        """, (session["candidato_id"], ))

    candidaturas = cursor.fetchall()
    conn.close()

    return render_template("minhas_candidaturas.html",
                           candidaturas=candidaturas)


@candidaturas_bp.route("/cancelar_candidatura", methods=["POST"])
def cancelar_candidatura():
    if "candidato_id" not in session:
        return jsonify({"error": "Não autorizado"}), 401

    data = request.get_json()
    vaga_id = data.get("vaga_id")

    conn = get_db_connection()
    cursor = conn.cursor()

    # Verificar se a candidatura existe
    cursor.execute(
        "SELECT id FROM candidaturas WHERE candidato_id = ? AND vaga_id = ?",
        (session["candidato_id"], vaga_id))
    candidatura = cursor.fetchone()

    if not candidatura:
        conn.close()
        return {"error": "Candidatura não encontrada"}, 404

    # Remover candidatura
    cursor.execute(
        "DELETE FROM candidaturas WHERE candidato_id = ? AND vaga_id = ?",
        (session["candidato_id"], vaga_id))

    # Recalcular posições dos candidatos restantes
    cursor.execute(
        """
        UPDATE candidaturas
        SET posicao = (
            SELECT COUNT(*) + 1
            FROM candidaturas c2
            WHERE c2.vaga_id = candidaturas.vaga_id
            AND c2.score > candidaturas.score
        )
        WHERE vaga_id = ?
    """, (vaga_id, ))

    conn.commit()
    conn.close()

    return {"success": True}


@candidaturas_bp.route("/editar_perfil_candidato", methods=["GET", "POST"])
def editar_perfil_candidato():
    if "candidato_id" not in session:
        return redirect(url_for("auth.login_candidato"))

    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == "POST":
        nome = request.form["nome"]
        telefone = request.form["telefone"]
        linkedin = request.form["linkedin"]
        pretensao_salarial = float(request.form["pretensao_salarial"])
        experiencia = request.form["experiencia"]
        competencias = request.form["competencias"]
        resumo_profissional = request.form["resumo_profissional"]

        cursor.execute(
            """
            UPDATE candidatos
            SET nome = ?, telefone = ?, linkedin = ?, pretensao_salarial = ?,
                experiencia = ?, competencias = ?, resumo_profissional = ?
            WHERE id = ?
        """, (nome, telefone, linkedin, pretensao_salarial, experiencia,
              competencias, resumo_profissional, session["candidato_id"]))

        conn.commit()
        conn.close()

        flash("Perfil atualizado com sucesso!", "success")
        return redirect(url_for("candidaturas.dashboard_candidato"))

    cursor.execute(
        """
        SELECT nome, telefone, linkedin, pretensao_salarial,
               experiencia, competencias, resumo_profissional
        FROM candidatos WHERE id = ?
    """, (session["candidato_id"], ))

    candidato = cursor.fetchone()
    conn.close()

    return render_template("editar_perfil_candidato.html", candidato=candidato)


@candidaturas_bp.route("/baixar_curriculo/<int:candidato_id>")
def baixar_curriculo(candidato_id):
    if "empresa_id" not in session:
        return redirect(url_for("auth.login_empresa"))

    conn = get_db_connection()
    cursor = conn.cursor()

    # Verificar se a empresa tem acesso ao candidato (através de candidatura)
    cursor.execute(
        """
        SELECT COUNT(*) FROM candidaturas ca
        JOIN vagas v ON ca.vaga_id = v.id
        WHERE ca.candidato_id = ? AND v.empresa_id = ?
    """, (candidato_id, session["empresa_id"]))

    if cursor.fetchone()[0] == 0:
        flash("Acesso negado ao currículo", "error")
        return redirect(url_for("vagas.dashboard_empresa"))

    # Buscar dados do candidato
    cursor.execute(
        """
        SELECT nome, caminho_curriculo
        FROM candidatos WHERE id = ?
    """, (candidato_id, ))

    candidato = cursor.fetchone()
    conn.close()

    if not candidato:
        flash("Candidato não encontrado", "error")
        return redirect(url_for("vagas.dashboard_empresa"))

    # Verificar se o arquivo do currículo existe
    if not candidato[1]:
        flash("Currículo não disponível para download", "error")
        return redirect(url_for("vagas.dashboard_empresa"))

    caminho_curriculo = os.path.join("uploads", candidato[1])

    if not os.path.exists(caminho_curriculo):
        flash("Arquivo do currículo não encontrado", "error")
        return redirect(url_for("vagas.dashboard_empresa"))

    nome_download = f"curriculo_{candidato[0].replace(' ', '_')}.pdf"

    return send_file(caminho_curriculo,
                     as_attachment=True,
                     download_name=nome_download,
                     mimetype="application/pdf")


@candidaturas_bp.route("/api/candidatos_vaga/<int:vaga_id>")
def api_candidatos_vaga(vaga_id):
    if "empresa_id" not in session:
        return jsonify({"error": "Não autorizado"}), 401

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """SELECT c.id, c.nome, ca.score
           FROM candidaturas ca
           JOIN candidatos c ON ca.candidato_id = c.id
           JOIN vagas v ON ca.vaga_id = v.id
           WHERE ca.vaga_id = ? AND v.empresa_id = ?
           ORDER BY ca.score DESC""", (vaga_id, session["empresa_id"]))

    candidatos = cursor.fetchall()
    conn.close()

    return jsonify([{
        "id": c[0],
        "nome": c[1],
        "score": round(c[2], 1)
    } for c in candidatos])


@candidaturas_bp.route("/api/score-detalhes/<int:candidato_id>/<int:vaga_id>")
def api_score_detalhes(candidato_id, vaga_id):
    """API para obter detalhes do cálculo do score"""
    if "empresa_id" not in session:
        return jsonify({"error": "Não autorizado"}), 401

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Verificar se a empresa tem acesso ao candidato
        cursor.execute(
            """
            SELECT c.texto_curriculo, c.pretensao_salarial, c.endereco_completo,
                   v.requisitos, v.salario_oferecido, v.diferenciais, v.tipo_vaga, v.endereco_vaga
            FROM candidatos c, vagas v
            WHERE c.id = ? AND v.id = ? AND v.empresa_id = ?
        """, (candidato_id, vaga_id, session["empresa_id"]))

        resultado = cursor.fetchone()
        if not resultado:
            return jsonify({"error": "Dados não encontrados"}), 404

        curriculo, pretensao_salarial, candidato_endereco, requisitos, salario_oferecido, diferenciais, tipo_vaga, vaga_endereco = resultado

        # Calcular score detalhado
        # Usar o método local que retorna detalhes
        from avaliador.avaliador_local import AvaliadorLocal
        avaliador_local = AvaliadorLocal()

        score_salarial = avaliador_local._calcular_score_salarial(
            pretensao_salarial, salario_oferecido)
        score_requisitos = avaliador_local._calcular_score_requisitos_avancado(
            curriculo, requisitos)
        score_experiencia = avaliador_local._calcular_score_experiencia(
            curriculo)
        score_diferenciais = avaliador_local._calcular_score_diferenciais(
            curriculo, diferenciais)
        score_localizacao = avaliador_local._calcular_score_localizacao(
            candidato_endereco, vaga_endereco, tipo_vaga)
        score_formacao = avaliador_local._calcular_score_formacao(
            curriculo, requisitos)

        # Gerar explicações
        detalhes = {
            "salarial":
            round(score_salarial, 1),
            "requisitos":
            round(score_requisitos, 1),
            "experiencia":
            round(score_experiencia, 1),
            "diferenciais":
            round(score_diferenciais, 1),
            "localizacao":
            round(score_localizacao, 1),
            "formacao":
            round(score_formacao, 1),
            "explicacao_salarial":
            gerar_explicacao_salarial(pretensao_salarial, salario_oferecido),
            "explicacao_requisitos":
            gerar_explicacao_requisitos(curriculo, requisitos),
            "explicacao_experiencia":
            gerar_explicacao_experiencia(curriculo),
            "explicacao_diferenciais":
            "Baseado em certificações e habilidades extras identificadas",
            "explicacao_localizacao":
            gerar_explicacao_localizacao(candidato_endereco, vaga_endereco,
                                         tipo_vaga),
            "explicacao_formacao":
            gerar_explicacao_formacao(curriculo, requisitos)
        }

        return jsonify(detalhes)

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

def gerar_explicacao_salarial(pretensao, oferecido):
    """Gera explicação para o score salarial"""
    if not pretensao or not oferecido:
        return "Sem informação salarial suficiente"

    if oferecido >= pretensao:
        diferenca = ((oferecido / pretensao) - 1) * 100
        return f"Salário oferecido é {diferenca:.0f}% superior à pretensão"
    else:
        diferenca = ((pretensao / oferecido) - 1) * 100
        return f"Pretensão é {diferenca:.0f}% acima do oferecido"


def gerar_explicacao_requisitos(curriculo, requisitos):
    """Gera explicação para o score de requisitos"""
    if not curriculo or not requisitos:
        return "Dados insuficientes para análise"

    from avaliador.avaliador_local import AvaliadorLocal
    avaliador = AvaliadorLocal()

    tecnologias_vaga = avaliador._extrair_tecnologias(requisitos.lower())
    tecnologias_candidato = avaliador._extrair_tecnologias(curriculo.lower())
    matches = len(
        [tech for tech in tecnologias_vaga if tech in tecnologias_candidato])

    if tecnologias_vaga:
        percentual = (matches / len(tecnologias_vaga)) * 100
        return f"Atende {matches} de {len(tecnologias_vaga)} tecnologias ({percentual:.0f}%)"

    return "Análise baseada em compatibilidade geral de habilidades"


def gerar_explicacao_experiencia(curriculo):
    """Gera explicação para o score de experiência"""
    if not curriculo:
        return "Currículo não disponível"

    curriculo_lower = curriculo.lower()

    if any(palavra in curriculo_lower
           for palavra in ["senior", "sênior", "líder", "lead"]):
        return "Perfil Senior identificado"
    elif any(palavra in curriculo_lower for palavra in ["pleno", "analista"]):
        return "Perfil Pleno identificado"
    elif any(palavra in curriculo_lower
             for palavra in ["junior", "júnior", "estagiário", "estagio"]):
        return "Perfil Junior/Estagiário identificado"
    else:
        return "Nível de experiência não especificado claramente"


def gerar_explicacao_localizacao(candidato_endereco, vaga_endereco, tipo_vaga):
    """Gera explicação para o score de localização"""
    if tipo_vaga == "Remoto":
        return "Vaga remota, localização não é um fator"
    if not candidato_endereco or not vaga_endereco:
        return "Endereços não informados para cálculo de distância"

    from utils.helpers import calcular_distancia_endereco
    distancia = calcular_distancia_endereco(candidato_endereco, vaga_endereco)

    if distancia is not None:
        return f"Distância entre candidato e vaga: {distancia:.2f} km"
    else:
        return "Não foi possível calcular a distância entre os endereços"


def gerar_explicacao_formacao(curriculo, requisitos):
    """Gera explicação para o score de formação"""
    if not curriculo or not requisitos:
        return "Dados insuficientes para análise"

    curriculo_lower = curriculo.lower()
    requisitos_lower = requisitos.lower()

    if any(form in curriculo_lower
           for form in ["mestrado", "doutorado", "phd"]):
        return "Pós-graduação stricto sensu identificada"
    elif any(form in curriculo_lower
             for form in ["mba", "especialização", "pós-graduação"]):
        return "Pós-graduação lato sensu identificada"
    elif any(form in curriculo_lower
             for form in ["graduação", "bacharelado", "licenciatura"]):
        return "Ensino superior completo"
    else:
        return "Formação baseada no perfil profissional"


@candidaturas_bp.route("/candidatos-geral")
def candidatos_geral():
    """Página para visualizar todos os candidatos cadastrados"""
    if "empresa_id" not in session:
        return redirect(url_for("auth.login_empresa"))

    return render_template("candidatos_geral.html")


@candidaturas_bp.route("/api/candidatos-geral")
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
                   c.endereco_completo, c.pretensao_salarial, c.competencias,
                   c.texto_curriculo, COALESCE(c.data_cadastro, datetime("now")) as data_cadastro,
                   CASE WHEN c.texto_curriculo IS NOT NULL AND c.texto_curriculo != '' THEN 1 ELSE 0 END as tem_curriculo,
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
                "endereco_completo": row[5] or "",
                "pretensao_salarial": row[6] or 0,
                "competencias": row[7] or "",
                "texto_curriculo": row[8] or "",
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


@candidaturas_bp.route("/empresa/candidatos-favoritos")
def candidatos_favoritos():
    """Página para visualizar candidatos favoritos"""
    if "empresa_id" not in session:
        return redirect(url_for("auth.login_empresa"))

    return render_template("candidatos_favoritos.html")


@candidaturas_bp.route("/api/candidatos-favoritos")
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


@candidaturas_bp.route("/api/favoritar-candidato", methods=["POST"])
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


@candidaturas_bp.route("/api/favoritar-candidato-geral", methods=["POST"])
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


@candidaturas_bp.route("/api/favoritar-vaga", methods=["POST"])
def favoritar_vaga():
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


@candidaturas_bp.route("/api/dicas-favoritas")
def obter_dicas_favoritas():
    candidato_id = session.get("candidato_id")
    if not candidato_id:
        return jsonify({"success": False, "error": "Não autorizado"}), 401

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Buscar vagas favoritas do candidato
        cursor.execute("""
            SELECT v.id, v.titulo, v.descricao, v.requisitos, v.salario_oferecido, 
                   v.tipo_vaga, e.nome as empresa_nome, f.data_adicao as data_favoritado
            FROM candidato_vaga_favorita f
            JOIN vagas v ON f.vaga_id = v.id
            JOIN empresas e ON v.empresa_id = e.id
            WHERE f.candidato_id = ? AND v.status = 'Ativa'
            ORDER BY f.data_adicao DESC
            LIMIT 10
        """, (candidato_id,))

        vagas_favoritas = cursor.fetchall()

        if not vagas_favoritas:
            return jsonify({
                "success": False, 
                "message": "Adicione vagas aos favoritos para receber dicas personalizadas"
            })

        # Buscar dados do candidato
        cursor.execute("""
            SELECT nome, email, competencias, experiencia, resumo_profissional, pretensao_salarial
            FROM candidatos 
            WHERE id = ?
        """, (candidato_id,))

        candidato_data = cursor.fetchone()
        if not candidato_data:
            return jsonify({"success": False, "error": "Candidato não encontrado"}), 404

        # Gerar dicas baseadas nas vagas favoritas
        dicas = gerar_dicas_personalizadas(vagas_favoritas, candidato_data)

        return jsonify({
            "success": True,
            "dicas": dicas,
            "vagas_analisadas": len(vagas_favoritas)
        })

    except Exception as e:
        print(f"Erro ao gerar dicas favoritas: {e}")
        return jsonify({"success": False, "error": "Erro interno"}), 500
    finally:
        conn.close()


from collections import Counter

def gerar_dicas_personalizadas(vagas_favoritas, candidato_data):
    """Gera dicas personalizadas baseadas nas vagas favoritas"""
    dicas = []

    nome, email, competencias, experiencia, resumo_prof, pretensao_salarial = candidato_data

    # Analisar requisitos mais comuns
    todos_requisitos = []
    salarios = []
    tipos_vaga = []

    for vaga in vagas_favoritas:
        vaga_id, titulo, descricao, requisitos, salario, tipo_vaga, empresa, data_fav = vaga
        if requisitos:
            todos_requisitos.extend(requisitos.lower().split())
        salarios.append(salario)
        tipos_vaga.append(tipo_vaga)

    # Palavras-chave mais frequentes
    palavras_freq = Counter(todos_requisitos)
    skills_demandadas = [palavra for palavra, freq in palavras_freq.most_common(10) 
                        if len(palavra) > 3 and palavra not in ["para", "com", "das", "dos", "uma", "ser", "sua", "seus", "mais", "pelo", "pela", "como", "este", "esta", "você"]]

    # Dica 1: Competências em alta
    if skills_demandadas:
        competencias_usuario = competencias.lower() if competencias else ""
        skills_faltando = [skill for skill in skills_demandadas[:5] 
                          if skill not in competencias_usuario]

        if skills_faltando:
            dicas.append({
                "categoria": "competencias",
                "titulo": "Competências em Alta Demanda",
                "descricao": f"As vagas que você favoritou frequentemente mencionam: {', '.join(skills_faltando[:3])}. Considere desenvolver essas habilidades.",
                "acao": f"Procure cursos online sobre \"{skills_faltando[0]}\" ou adicione projetos relacionados ao seu portfólio."
            })

    # Dica 2: Faixa salarial
    if salarios:
        salario_medio = sum(salarios) / len(salarios)
        if pretensao_salarial and pretensao_salarial < salario_medio * 0.8:
            dicas.append({
                "categoria": "negociacao",
                "titulo": "Potencial de Negociação Salarial",
                "descricao": f"As vagas favoritas oferecem em média R$ {salario_medio:,.2f}, enquanto sua pretensão é R$ {pretensao_salarial:,.2f}.",
                "acao": "Considere revisar sua pretensão salarial ou destacar mais suas qualificações para justificar um valor maior."
            })

    # Dica 3: Modalidade de trabalho
    if tipos_vaga:
        tipo_mais_comum = max(set(tipos_vaga), key=tipos_vaga.count)
        dica_modalidade = {
            "categoria": "preparacao",
            "titulo": f"Preparação para Trabalho {tipo_mais_comum}",
            "descricao": f"A maioria das suas vagas favoritas é do tipo {tipo_mais_comum}. Prepare-se adequadamente para essa modalidade.",
            "acao": ""
        }
        if tipo_mais_comum == "Remoto":
            dica_modalidade["acao"] = "Configure um ambiente de trabalho adequado em casa, com boa conexão e ergonomia."
        elif tipo_mais_comum == "Presencial":
            dica_modalidade["acao"] = "Prepare-se para deslocamentos, horários presenciais e interações no escritório."
        elif tipo_mais_comum == "Híbrido":
            dica_modalidade["acao"] = "Organize-se para alternar entre home office e escritório, gerenciando bem seu tempo."
        
        dicas.append(dica_modalidade)

    # Dica 4: Perfil profissional
    if not resumo_prof or len(resumo_prof) < 100:
        dicas.append({
            "categoria": "perfil",
            "titulo": "Melhore seu Resumo Profissional",
            "descricao": "Um resumo profissional bem estruturado pode aumentar suas chances de ser notado.",
            "acao": "Escreva um resumo de 2-3 parágrafos destacando suas principais conquistas, habilidades e objetivos profissionais."
        })

    # Dica 5: Networking
    empresas_favoritas = list(set([vaga[6] for vaga in vagas_favoritas]))
    if len(empresas_favoritas) > 2:
        dicas.append({
            "categoria": "networking",
            "titulo": "Oportunidades de Networking",            "descricao": f"Você demonstrou interesse em empresas como: {', '.join(empresas_favoritas[:3])}.",
            "acao": "Pesquise profissionais dessas empresas no LinkedIn e tente estabelecer conexões relevantes."
        })

    return dicas


