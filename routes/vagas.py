from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from flask import request, jsonify, session, redirect, url_for, flash
from db import get_db_connection
from datetime import datetime, timedelta
from ia_utils import gerar_feedback_ia_vaga_cached
from config import get_config
from avaliador import get_avaliador
vagas_bp = Blueprint("vagas", __name__)

@vagas_bp.route("/")
def index():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        '''SELECT v.id, v.titulo, v.descricao, v.requisitos, v.salario_oferecido,
                  v.tipo_vaga, v.diferenciais, e.nome as empresa_nome,
                  v.localizacao_cidade, v.localizacao_estado
           FROM vagas v
           JOIN empresas e ON v.empresa_id = e.id
           WHERE v.status = 'Ativa'
           ORDER BY v.data_criacao DESC
           LIMIT 10''') # Limitando a 10 vagas mais recentes

    vagas_raw = cursor.fetchall()

    # Processar as vagas para o template
    vagas = []
    for vaga in vagas_raw:
        vaga_dict = {
            'id':
            vaga[0],
            'titulo':
            vaga[1],
            'descricao':
            vaga[2][:100] +
            '...' if len(vaga[2]) > 100 else vaga[2],  # Truncar descrição
            'requisitos':
            vaga[3],
            'salario_oferecido':
            vaga[4],
            'tipo_vaga':
            vaga[5] or 'Presencial',
            'diferenciais':
            vaga[6] or '',
            'empresa_nome':
            vaga[7],
            'localizacao':
            f"{vaga[8]}, {vaga[9]}" if vaga[8] and vaga[9] else
            (vaga[8] or vaga[9] or 'Não informado')
        }
        vagas.append(vaga_dict)

    return render_template('index.html', vagas=vagas)


@vagas_bp.route("/vaga-publico/<int:vaga_id>")
def detalhes_vaga_publico(vaga_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        '''
        SELECT v.*, e.nome as empresa_nome
        FROM vagas v
        JOIN empresas e ON v.empresa_id = e.id
        WHERE v.id = %s AND v.status = 'Ativa'
    ''', (vaga_id,))
    vaga_data = cursor.fetchone()

    if not vaga_data:
        flash('Vaga não encontrada ou não está mais ativa', 'error')
        return redirect(url_for('index'))

     # Tratar a data de criação
    data_criacao = vaga_data[6]
    if data_criacao and isinstance(data_criacao, str):
        try:
            data_criacao = datetime.strptime(data_criacao, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            pass


    # Estruturar dados da vaga
    vaga = {
        'id': vaga_data[0],
        'titulo': vaga_data[2],
        'descricao': vaga_data[3],
        'requisitos': vaga_data[4],
        'salario_oferecido': vaga_data[5],
        'tipo_vaga': vaga_data[7] or 'Presencial',
        'endereco_vaga': vaga_data[8],
        'diferenciais': vaga_data[11],
        'data_criacao': data_criacao
    }

    empresa = {'nome': vaga_data[12]}

    return render_template(
        'detalhes_vaga_publico.html',
        vaga=vaga,
        empresa=empresa
    )



@vagas_bp.route("/dashboard_empresa")
def dashboard_empresa():
    if 'empresa_id' not in session or session.get('tipo_usuario') != 'empresa':
        flash('Faça login para acessar esta página', 'error')
        return redirect(url_for('login_empresa'))

    conn = get_db_connection()
    cursor = conn.cursor()

    # Pega dados da empresa (inclui imagem_perfil e nome)
    cursor.execute("SELECT id, nome, imagem_perfil FROM empresas WHERE id = %s", (session['empresa_id'],))
    empresa = cursor.fetchone()

    # Query otimizada com índices e CTEs para contagem de candidatos
    cursor.execute(
        '''
        WITH CandidatoStats AS (
            SELECT 
                vaga_id,
                COUNT(*) as total_candidatos,
                SUM(CASE WHEN score >= 80 THEN 1 ELSE 0 END) as candidatos_80_plus,
                SUM(CASE WHEN score >= 60 AND score < 80 THEN 1 ELSE 0 END) as candidatos_60_79,
                SUM(CASE WHEN score < 60 THEN 1 ELSE 0 END) as candidatos_abaixo_60
            FROM candidaturas
            GROUP BY vaga_id
        )
        SELECT 
            v.id, v.empresa_id, v.titulo, v.descricao, v.requisitos, v.salario_oferecido, 
            v.data_criacao, v.tipo_vaga, v.endereco_vaga, v.status, v.candidato_selecionado_id, 
            v.diferenciais,
            COALESCE(cs.total_candidatos, 0) as total_candidatos,
            COALESCE(cs.candidatos_80_plus, 0) as candidatos_80_plus,
            COALESCE(cs.candidatos_60_79, 0) as candidatos_60_79,
            COALESCE(cs.candidatos_abaixo_60, 0) as candidatos_abaixo_60,
            c.nome as candidato_contratado_nome
        FROM vagas v
        LEFT JOIN CandidatoStats cs ON v.id = cs.vaga_id
        LEFT JOIN candidatos c ON v.candidato_selecionado_id = c.id
        WHERE v.empresa_id = %s
        ORDER BY v.data_criacao DESC
        ''', (session['empresa_id'], ))

    vagas_com_stats = cursor.fetchall()
    conn.close()

    vagas_processadas = []
    for vaga in vagas_com_stats:
        # Formatação de data segura
        data_criacao = 'N/A'
        try:
            valor_data = vaga[6]  # data_criacao
            if isinstance(valor_data, datetime):
                data_criacao = valor_data.strftime('%d/%m/%Y')
            elif isinstance(valor_data, str):
                try:
                    data_criacao = datetime.strptime(valor_data, '%Y-%m-%d %H:%M:%S').strftime('%d/%m/%Y')
                except ValueError:
                    data_criacao = datetime.strptime(valor_data, '%Y-%m-%d').strftime('%d/%m/%Y')
            elif isinstance(valor_data, (int, float)):
                data_criacao = datetime.utcfromtimestamp(valor_data).strftime('%d/%m/%Y')
        except Exception:
            data_criacao = 'N/A'

        # Conversão segura para inteiros
        total_candidatos = int(vaga[12] or 0)
        candidatos_80_plus = int(vaga[13] or 0)
        candidatos_60_79 = int(vaga[14] or 0)
        candidatos_abaixo_60 = int(vaga[15] or 0)

        vaga_dict = {
            'id': vaga[0],
            'empresa_id': vaga[1],
            'titulo': vaga[2],
            'descricao': vaga[3],
            'requisitos': vaga[4],
            'salario_oferecido': vaga[5],
            'diferenciais': vaga[11] or '',
            'tipo_vaga': vaga[7] or 'Presencial',
            'endereco_vaga': vaga[8] or '',
            'status': vaga[9] or 'Ativa',
            'candidato_selecionado_id': vaga[10],
            'data_criacao': data_criacao,
            'total_candidatos': total_candidatos,
            'candidatos_80_plus': candidatos_80_plus,
            'candidatos_60_79': candidatos_60_79,
            'candidatos_abaixo_60': candidatos_abaixo_60,
            'candidato_contratado': {
                'nome': vaga[16]
            } if vaga[9] == 'Concluída' and vaga[16] else None,
            'feedback_ia': gerar_feedback_ia_vaga_cached(
                total_candidatos,
                candidatos_80_plus,
                candidatos_60_79,
                candidatos_abaixo_60
            )
        }
        vagas_processadas.append(vaga_dict)

    return render_template('empresa/dashboard_empresa.html',
                           imagem_perfil_empresa=empresa[2], 
                           vagas=vagas_processadas)



@vagas_bp.route("/criar_vaga", methods=["GET", "POST"])
def criar_vaga():
    if 'empresa_id' not in session:
        return redirect(url_for('login_empresa'))

    if request.method == 'POST':
        titulo = request.form['titulo']
        descricao = request.form['descricao']
        requisitos = request.form['requisitos']
        salario_oferecido = float(request.form['salario_oferecido'])
        tipo_vaga = request.form['tipo_vaga']
        diferenciais = request.form.get('diferenciais', '')

        categoria_id = request.form.get('categoria_id') or None
        nova_categoria = request.form.get('nova_categoria', '').strip()
        urgencia_contratacao = request.form.get('urgencia_contratacao', '')
        data_congelamento_agendado = request.form.get('data_congelamento_agendado') or None
        usar_endereco_empresa = 'usar_endereco_empresa' in request.form

        localizacao_endereco = request.form.get('localizacao_endereco', '')
        localizacao_cidade = request.form.get('localizacao_cidade', '')
        localizacao_estado = request.form.get('localizacao_estado', '')
        localizacao_cep = request.form.get('localizacao_cep', '')

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            # Criar nova categoria, se aplicável
            if nova_categoria and (not categoria_id or categoria_id == 'nova'):
                cursor.execute('INSERT IGNORE INTO categorias (nome) VALUES (%s)', (nova_categoria,))
                cursor.execute('SELECT id FROM categorias WHERE nome = %s', (nova_categoria,))
                categoria_result = cursor.fetchone()
                if categoria_result:
                    categoria_id = categoria_result[0]

            # Buscar endereço da empresa, se solicitado
            if usar_endereco_empresa:
                cursor.execute('SELECT endereco, cidade, estado, cep FROM empresas WHERE id = %s',
                               (session['empresa_id'], ))
                endereco_empresa = cursor.fetchone()
                if endereco_empresa:
                    localizacao_endereco = endereco_empresa[0] or localizacao_endereco
                    localizacao_cidade = endereco_empresa[1] or localizacao_cidade
                    localizacao_estado = endereco_empresa[2] or localizacao_estado
                    localizacao_cep = endereco_empresa[3] or localizacao_cep

            # Validar data de congelamento agendado
            if data_congelamento_agendado:
                try:
                    congelamento_date = datetime.strptime(data_congelamento_agendado, '%Y-%m-%d')
                    if congelamento_date <= datetime.now():
                        flash('A data de congelamento precisa ser uma data futura.', 'error')
                        return redirect(url_for('criar_vaga'))
                except ValueError:
                    flash('Data de congelamento inválida.', 'error')
                    return redirect(url_for('criar_vaga'))

            # Inserir nova vaga
            cursor.execute(
                '''
                INSERT INTO vagas (
                    titulo, descricao, requisitos, salario_oferecido, tipo_vaga, diferenciais,
                    empresa_id, data_criacao, status, categoria_id, urgencia_contratacao,
                    data_congelamento_agendado, usar_endereco_empresa, localizacao_endereco,
                    localizacao_cidade, localizacao_estado, localizacao_cep
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'Ativa', %s, %s, %s, %s, %s, %s, %s, %s)
                ''',
                (titulo, descricao, requisitos, salario_oferecido, tipo_vaga,
                 diferenciais, session['empresa_id'],
                 datetime.now(), categoria_id,
                 urgencia_contratacao, data_congelamento_agendado,
                 int(usar_endereco_empresa), localizacao_endereco,
                 localizacao_cidade, localizacao_estado, localizacao_cep)
            )

            conn.commit()
            flash('Vaga criada com sucesso!', 'success')
            return redirect(url_for('dashboard_empresa'))

        except Exception as e:
            flash(f'Erro ao criar vaga: {str(e)}', 'error')
            print(f"Erro detalhado: {e}")
        finally:
            conn.close()

    # GET: renderizar formulário
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, nome FROM categorias ORDER BY nome')
    categorias = [{'id': row[0], 'nome': row[1]} for row in cursor.fetchall()]
    conn.close()

    hoje = datetime.now().strftime('%Y-%m-%d')

    return render_template('/empresa/criar_vaga.html', categorias=categorias, hoje=hoje)



@vagas_bp.route("/editar_vaga/<int:vaga_id>", methods=["GET", "POST"])
def editar_vaga(vaga_id):
    if "empresa_id" not in session:
        flash("Acesso negado", "error")
        return redirect(url_for("auth.login_empresa"))

    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == "POST":
        titulo = request.form["titulo"]
        descricao = request.form["descricao"]
        requisitos = request.form["requisitos"]
        salario_oferecido = float(request.form["salario_oferecido"])
        tipo_vaga = request.form["tipo_vaga"]
        diferenciais = request.form.get("diferenciais", "")

        # Novos campos
        turno_trabalho = request.form.get("turno_trabalho", "Comercial")
        nivel_experiencia = request.form.get("nivel_experiencia", "Júnior")
        regime_contratacao = request.form.get("regime_contratacao", "CLT")
        carga_horaria = request.form.get("carga_horaria", "40h")
        formacao_minima = request.form.get("formacao_minima", "Ensino Médio")
        idiomas_exigidos = request.form.get("idiomas_exigidos", "")
        disponibilidade_viagens = "disponibilidade_viagens" in request.form
        beneficios = request.form.get("beneficios", "")
        data_limite_candidatura = request.form.get("data_limite_candidatura") or None


        categoria_id = request.form.get("categoria_id") or None
        nova_categoria = request.form.get("nova_categoria", "").strip()
        urgencia_contratacao = request.form.get("urgencia_contratacao", "")
        data_congelamento_agendado = request.form.get("data_congelamento_agendado") or None
        usar_endereco_empresa = "usar_endereco_empresa" in request.form

        # Campos de localização
        localizacao_endereco = request.form.get("localizacao_endereco", "")
        localizacao_cidade = request.form.get("localizacao_cidade", "")
        localizacao_estado = request.form.get("localizacao_estado", "")
        localizacao_cep = request.form.get("localizacao_cep", "")

        try:
            # Se nova categoria foi informada, criar/buscar categoria
            if nova_categoria and (not categoria_id or categoria_id == "nova"):
                cursor.execute("INSERT OR IGNORE INTO categorias (nome) VALUES (%s)",
                               (nova_categoria, ))
                cursor.execute("SELECT id FROM categorias WHERE nome = %s",
                               (nova_categoria, ))
                categoria_result = cursor.fetchone()
                if categoria_result:
                    categoria_id = categoria_result[0]

            # Se usar endereço da empresa, buscar dados da empresa
            if usar_endereco_empresa:
                cursor.execute("SELECT endereco, cidade, estado, cep FROM empresas WHERE id = %s",
                               (session["empresa_id"], ))
                endereco_empresa = cursor.fetchone()
                if endereco_empresa:
                    localizacao_endereco = endereco_empresa[0] or localizacao_endereco
                    localizacao_cidade = endereco_empresa[1] or localizacao_cidade
                    localizacao_estado = endereco_empresa[2] or localizacao_estado
                    localizacao_cep = endereco_empresa[3] or localizacao_cep

            cursor.execute(
                """
                UPDATE vagas
                SET titulo = %s, descricao = %s, requisitos = %s, salario_oferecido = %s, tipo_vaga = %s, diferenciais = %s,
                    categoria_id = %s, urgencia_contratacao = %s, data_congelamento_agendado = %s, usar_endereco_empresa = %s,
                    localizacao_endereco = %s, localizacao_cidade = %s, localizacao_estado = %s, localizacao_cep = %s,
                    turno_trabalho = %s, nivel_experiencia = %s, regime_contratacao = %s, carga_horaria = %s,
                    formacao_minima = %s, idiomas_exigidos = %s, disponibilidade_viagens = %s, beneficios = %s,
                    data_limite_candidatura = %s
                WHERE id = %s
            """, (titulo, descricao, requisitos, salario_oferecido, tipo_vaga,
                  diferenciais, categoria_id, urgencia_contratacao,
                  data_congelamento_agendado, usar_endereco_empresa,
                  localizacao_endereco, localizacao_cidade, localizacao_estado,
                  localizacao_cep, turno_trabalho, nivel_experiencia, regime_contratacao,
                  carga_horaria, formacao_minima, idiomas_exigidos, int(disponibilidade_viagens),
                  beneficios, data_limite_candidatura, vaga_id))

            conn.commit()
            flash("Vaga atualizada com sucesso!", "success")
            return redirect(url_for("vagas.dashboard_empresa"))

        except Exception as e:
            flash(f"Erro ao atualizar vaga: {str(e)}", "error")
            print(f"Erro detalhado: {e}")

    # Buscar dados da vaga para exibição (funciona tanto para GET quanto para POST com erro)
    cursor.execute(
        """
        SELECT v.*, c.nome as categoria_nome
        FROM vagas v
        LEFT JOIN categorias c ON v.categoria_id = c.id
        WHERE v.id = %s
    """, (vaga_id, ))
    vaga_completa = cursor.fetchone()

    if vaga_completa:
        colunas = [desc[0] for desc in cursor.description]
        vaga = dict(zip(colunas, vaga_completa))
    else:
        vaga = {}
        flash("Vaga não encontrada", "error")
        return redirect(url_for("vagas.dashboard_empresa"))

    # Buscar categorias para o formulário
    cursor.execute("SELECT id, nome FROM categorias ORDER BY nome")
    categorias = [{"id": row[0], "nome": row[1]} for row in cursor.fetchall()]

    conn.close()

    return render_template("empresa/editar_vaga.html",
                           vaga=vaga,
                           categorias=categorias,
                           datetime=datetime,
                           timedelta=timedelta)


@vagas_bp.route("/editar_perfil_empresa", methods=["GET", "POST"])
def editar_perfil_empresa():
    if "empresa_id" not in session:
        return redirect(url_for("auth.login_empresa"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    empresa_id = session["empresa_id"]

    if request.method == "POST":
        # Campos do formulário
        nome = request.form["nome"]
        email = request.form["email"]
        endereco = request.form.get("endereco")
        estado = request.form.get("estado")
        cidade = request.form.get("cidade")
        cep = request.form.get("cep")

        # Processamento da imagem igual ao candidato
        imagem_perfil_url = None
        if "imagem_perfil" in request.files:
            imagem_file = request.files["imagem_perfil"]
            if imagem_file and imagem_file.filename != "":
                from routes.arquivos import upload_imagem_perfil
                resultado = upload_imagem_perfil(imagem_file, nome_usuario=f"empresa_{empresa_id}")
                if resultado["sucesso"]:
                    imagem_perfil_url = resultado["url"]
                else:
                    flash(f"Erro ao enviar imagem: {resultado['erro']}", "danger")

        # Construir query de atualização
        update_query = """
            UPDATE empresas
            SET nome=%s, email=%s, endereco=%s, estado=%s, cidade=%s, cep=%s
        """
        params = [nome, email, endereco, estado, cidade, cep]

        if imagem_perfil_url:
            update_query += ", imagem_perfil=%s"
            params.append(imagem_perfil_url)

        update_query += " WHERE id=%s"
        params.append(empresa_id)

        cursor.execute(update_query, tuple(params))
        conn.commit()
        conn.close()

        flash("Perfil da empresa atualizado com sucesso!", "success")
        return redirect(url_for("vagas.dashboard_empresa"))

    # GET – carregar dados atuais
    cursor.execute(
        """
        SELECT nome, email, endereco, estado, cidade, cep, imagem_perfil
        FROM empresas WHERE id = %s
        """,
        (empresa_id,),
    )
    empresa = cursor.fetchone()
    conn.close()

    return render_template("empresa/editar_perfil_empresa.html", empresa=empresa)


@vagas_bp.route('/exemplo-score')
def exemplo_score():
    return render_template('exemplo_score.html')


@vagas_bp.route("/vaga/<int:vaga_id>")
def detalhes_vaga(vaga_id):
    if "candidato_id" not in session:
        return redirect(url_for("auth.login_candidato"))

    conn = get_db_connection()
    cursor = conn.cursor()

    # Buscar dados da vaga e empresa
    cursor.execute(
        """
        SELECT v.id, v.empresa_id, v.titulo, v.descricao, v.requisitos, 
               v.salario_oferecido, v.data_criacao, v.tipo_vaga, v.endereco_vaga, 
               v.status, v.diferenciais, e.nome as empresa_nome
        FROM vagas v
        JOIN empresas e ON v.empresa_id = e.id
        WHERE v.id = %s AND v.status = 'Ativa'
        """,
        (vaga_id,)
    )
    vaga_data = cursor.fetchone()

    if not vaga_data:
        flash("Vaga não encontrada ou não está mais ativa", "error")
        conn.close()
        return redirect(url_for("candidaturas.dashboard_candidato"))

    # Buscar dados do candidato para calcular feedback
    cursor.execute(
        """
        SELECT resumo_profissional, endereco, pretensao_salarial
        FROM candidatos WHERE id = %s
        """,
        (session["candidato_id"],)
    )
    candidato_data = cursor.fetchone()

    # Verificar se já se candidatou
    cursor.execute(
        """
        SELECT id, score FROM candidaturas
        WHERE candidato_id = %s AND vaga_id = %s
        """,
        (session["candidato_id"], vaga_id)
    )
    candidatura = cursor.fetchone()

    conn.close()

    # Converter data_criacao para datetime se necessário
    data_criacao_raw = vaga_data[6]
    if data_criacao_raw:
        if isinstance(data_criacao_raw, str):
            data_criacao = datetime.strptime(data_criacao_raw, "%Y-%m-%d %H:%M:%S")
        else:
            data_criacao = data_criacao_raw
    else:
        data_criacao = None

    # Estruturar dados da vaga
    vaga = {
        "id": vaga_data[0],
        "empresa_id": vaga_data[1],
        "titulo": vaga_data[2],
        "descricao": vaga_data[3],
        "requisitos": vaga_data[4],
        "salario_oferecido": vaga_data[5],
        "data_criacao": data_criacao,
        "tipo_vaga": vaga_data[7] or "Presencial",
        "endereco_vaga": vaga_data[8],
        "status": vaga_data[9],
        "diferenciais": vaga_data[10],
    }

    empresa = {
        "nome": vaga_data[11]
    }

    score = None
    if candidato_data:
        config = get_config()
        avaliador = get_avaliador(config["MODO_IA"])

        score = candidatura[1] if candidatura else avaliador.calcular_score(
            candidato_data[0], vaga["requisitos"], candidato_data[2],
            vaga["salario_oferecido"], vaga["diferenciais"], candidato_data[1],
            vaga["endereco_vaga"], vaga["tipo_vaga"]
        )

    return render_template(
        "detalhes_vaga.html",
        vaga=vaga,
        empresa=empresa,
        score=score,
        ja_candidatado=bool(candidatura)
    )



@vagas_bp.route("/reativar_vaga/<int:vaga_id>", methods=["POST"])
def reativar_vaga_route(vaga_id):
    if "empresa_id" not in session:
        return jsonify({"error": "Não autorizado"}), 401

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE vagas SET status = 'Ativa' WHERE id = %s",
                   (vaga_id, ))
    conn.commit()
    conn.close()
    return redirect(url_for("vagas.dashboard_empresa"))


@vagas_bp.route("/api/todas-vagas")
def api_todas_vagas():
    """API para buscar todas as vagas disponíveis para o candidato"""
    if "candidato_id" not in session:
        return jsonify({"error": "Não autorizado"}), 401

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Buscar todas as vagas ativas
        cursor.execute(
            """
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
        """, (session["candidato_id"], session["candidato_id"]))

        vagas_raw = cursor.fetchall()

        # Buscar informações do candidato para calcular scores
        cursor.execute(
            "SELECT pretensao_salarial, resumo_profissional, endereco FROM candidatos WHERE id = %s",
            (session["candidato_id"], ))
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
                vaga[8], vaga[7])

            vaga_processada = {
                "id":
                int(vaga[0]),
                "titulo":
                vaga[1],
                "descricao":
                vaga[2],
                "requisitos":
                vaga[3],
                "salario_oferecido":
                float(vaga[4]) if vaga[4] else 0.0,
                "empresa_nome":
                vaga[5],
                "diferenciais":
                vaga[6] or "",
                "tipo_vaga":
                vaga[7] or "Presencial",
                "endereco_vaga":
                vaga[8] or "",
                "is_favorita":
                bool(vaga[9]),
                "ja_candidatou":
                bool(vaga[10]),
                "score":
                float(score)
            }
            vagas_processadas.append(vaga_processada)

        # Ordenar por score
        vagas_processadas.sort(key=lambda x: x["score"], reverse=True)

        return jsonify(vagas_processadas)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@vagas_bp.route("/api/busca-filtros")
def api_busca_filtros():
    """API para obter filtros disponíveis para busca"""
    if "candidato_id" not in session:
        return jsonify({"error": "Não autorizado"}), 401

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Buscar categorias
        cursor.execute("SELECT id, nome FROM categorias ORDER BY nome")
        categorias = [{
            "id": row[0],
            "nome": row[1]
        } for row in cursor.fetchall()]

        # Buscar localizações únicas das vagas ativas
        cursor.execute("""
            SELECT DISTINCT localizacao_cidade, localizacao_estado
            FROM vagas
            WHERE status = 'Ativa'
            AND (localizacao_cidade IS NOT NULL AND localizacao_cidade != '')
            ORDER BY localizacao_cidade
        """)

        localizacoes = []
        for row in cursor.fetchall():
            if row[0] and row[1]:
                localizacoes.append(f"{row[0]}, {row[1]}")
            elif row[0]:
                localizacoes.append(row[0])

        # Remover duplicatas e manter ordenação
        localizacoes = list(dict.fromkeys(localizacoes))

        return jsonify({
            "categorias": categorias,
            "localizacoes": localizacoes
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@vagas_bp.route("/api/buscar-vagas")
def api_buscar_vagas():
    """API para busca avançada de vagas com filtros"""
    if "candidato_id" not in session:
        return jsonify({"error": "Não autorizado"}), 401

    # Obter parâmetros de busca
    keyword = request.args.get("keyword", "").strip()
    location = request.args.get("location", "").strip()
    category = request.args.get("category", "").strip()
    urgency = request.args.get("urgency", "").strip()
    salary = request.args.get("salary", "").strip()
    job_type = request.args.get("type", "").strip()

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Construir query base
        query_base = """
            SELECT v.id, v.titulo, v.descricao, v.requisitos, v.salario_oferecido,
                   e.nome as empresa_nome, v.diferenciais, v.tipo_vaga, v.endereco_vaga,
                   CASE WHEN cvf.id IS NOT NULL THEN 1 ELSE 0 END as is_favorita,
                   CASE WHEN ca.id IS NOT NULL THEN 1 ELSE 0 END as ja_candidatou,
                   v.urgencia_contratacao, v.localizacao_cidade, v.localizacao_estado,
                   c.nome as categoria_nome,
                   v.turno_trabalho, v.nivel_experiencia, v.regime_contratacao, v.carga_horaria,
                   v.formacao_minima, v.idiomas_exigidos, v.disponibilidade_viagens,
                   v.beneficios, v.data_limite_candidatura
            FROM vagas v
            JOIN empresas e ON v.empresa_id = e.id
            LEFT JOIN candidato_vaga_favorita cvf ON cvf.candidato_id = %s AND cvf.vaga_id = v.id
            LEFT JOIN candidaturas ca ON ca.candidato_id = %s AND ca.vaga_id = v.id
            LEFT JOIN categorias c ON v.categoria_id = c.id
            WHERE v.status = 'Ativa'
        """

        params = [session["candidato_id"], session["candidato_id"]]

        # Adicionar filtros
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

        # Buscar informações do candidato para calcular scores
        cursor.execute(
            "SELECT pretensao_salarial, resumo_profissional, endereco FROM candidatos WHERE id = %s",
            (session["candidato_id"], ))
        candidato_info = cursor.fetchone()

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
                vaga[8], vaga[7])

            vaga_processada = {
                "id":
                int(vaga[0]),
                "titulo":
                vaga[1],
                "descricao":
                vaga[2],
                "requisitos":
                vaga[3],
                "salario_oferecido":
                float(vaga[4]) if vaga[4] else 0.0,
                "empresa_nome":
                vaga[5],
                "diferenciais":
                vaga[6] or "",
                "tipo_vaga":
                vaga[7] or "Presencial",
                "endereco_vaga":
                vaga[8] or "",
                "is_favorita":
                bool(vaga[9]),
                "ja_candidatou":
                bool(vaga[10]),
                "score":
                float(score),
                "turno_trabalho": vaga[15],
                "nivel_experiencia": vaga[16],
                "regime_contratacao": vaga[17],
                "carga_horaria": vaga[18],
                "formacao_minima": vaga[19],
                "idiomas_exigidos": vaga[20],
                "disponibilidade_viagens": bool(vaga[21]),
                "beneficios": vaga[22],
                "data_limite_candidatura": vaga[23]
            }
            vagas_processadas.append(vaga_processada)

        # Ordenar por score
        vagas_processadas.sort(key=lambda x: x["score"], reverse=True)

        return jsonify(vagas_processadas)

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@vagas_bp.route("/empresa/endereco")
def get_endereco_empresa():
    if "empresa_id" not in session:
        return jsonify({"error": "Não autorizado"}), 401

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "SELECT endereco, cidade, estado, cep FROM empresas WHERE id = %s",
            (session["empresa_id"], ))
        empresa = cursor.fetchone()

        if empresa:
            return jsonify({
                "endereco": empresa[0],
                "cidade": empresa[1],
                "estado": empresa[2],
                "cep": empresa[3]
            })
        else:
            return jsonify({"error": "Empresa não encontrada"}), 404

    finally:
        conn.close()


@vagas_bp.route("/api/vagas-empresa")
def api_vagas_empresa():
    """API para buscar vagas da empresa para filtros"""
    if "empresa_id" not in session:
        return jsonify({"error": "Não autorizado"}), 401

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT id, titulo, status FROM vagas WHERE empresa_id = %s ORDER BY titulo",
                       (session["empresa_id"], ))

        vagas = []
        for row in cursor.fetchall():
            vagas.append({"id": row[0], "titulo": row[1], "status": row[2]})

        return jsonify(vagas)

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()