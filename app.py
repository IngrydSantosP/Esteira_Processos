import os
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_file
from utils.helpers import inicializar_banco, calcular_distancia_endereco
from utils.resume_extractor import processar_upload_curriculo, finalizar_processamento_curriculo
from avaliador import criar_avaliador
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import io
import json
import sqlite3
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv
from datetime import datetime, timedelta
from utils.notifications import (obter_historico_notificacoes,
                                 contar_notificacoes_nao_lidas,
                                 marcar_notificacao_como_lida,
                                 marcar_todas_notificacoes_como_lidas,
                                 notification_system)
from utils.ia_assistant import IAAssistant
from scheduler import iniciar_scheduler_background

data_brasil = (datetime.utcnow() -
               timedelta(hours=3)).strftime('%Y-%m-%d %H:%M:%S')

load_dotenv()

app = Flask(__name__)

# Inicializar assistente IA
ia_assistant = IAAssistant()
app.secret_key = 'chave-secreta-mvp-recrutamento-2024'
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_TYPE'] = 'filesystem'

# Configurações do ambiente
MODO_IA = os.getenv('MODO_IA', 'local')
TOP_JOBS = int(os.getenv('TOP_JOBS', '3'))


def gerar_feedback_ia_vaga(total, alta_compatibilidade, media_compatibilidade,
                           baixa_compatibilidade):
    """Gera feedback inteligente sobre os candidatos da vaga"""
    # Garantir que todos os valores são inteiros
    total = total or 0
    alta_compatibilidade = alta_compatibilidade or 0
    media_compatibilidade = media_compatibilidade or 0
    baixa_compatibilidade = baixa_compatibilidade or 0

    if total == 0:
        return {
            'texto': 'Nenhum candidato ainda',
            'cor': 'text-gray-500',
            'icone': '📋'
        }

    if alta_compatibilidade > 0:
        percentual_alto = (alta_compatibilidade / total) * 100
        if percentual_alto >= 50:
            return {
                'texto':
                f'{alta_compatibilidade} candidato(s) com perfil excelente (80%+)',
                'cor': 'text-green-600',
                'icone': '🎯'
            }
        else:
            return {
                'texto':
                f'{alta_compatibilidade} candidato(s) muito compatível(eis)',
                'cor': 'text-green-500',
                'icone': '✅'
            }

    if media_compatibilidade > 0:
        return {
            'texto':
            f'{media_compatibilidade} candidato(s) com bom potencial (60-79%)',
            'cor': 'text-yellow-600',
            'icone': '⚡'
        }

    return {
        'texto': f'{total} candidato(s) - revisar requisitos da vaga',
        'cor': 'text-orange-500',
        'icone': '⚠️'
    }


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/login_empresa', methods=['GET', 'POST'])
def login_empresa():
    if request.method == 'POST':
        cnpj = request.form.get('cnpj', '').strip()
        senha = request.form.get('senha', '')

        if not cnpj or not senha:
            flash('Por favor, preencha todos os campos', 'error')
            return render_template('login_empresa.html')

        cnpj_limpo = ''.join(filter(str.isdigit, cnpj))

        if len(cnpj_limpo) != 14:
            flash('CNPJ deve ter exatamente 14 dígitos', 'error')
            return render_template('login_empresa.html')

        conn = sqlite3.connect('recrutamento.db')
        cursor = conn.cursor()

        try:
            cursor.execute(
                'SELECT id, senha_hash FROM empresas WHERE cnpj = ?',
                (cnpj_limpo, ))
            empresa = cursor.fetchone()

            if empresa and check_password_hash(empresa[1], senha):
                session.clear()
                session['empresa_id'] = empresa[0]
                session['tipo_usuario'] = 'empresa'
                session.permanent = True
                return redirect(url_for('dashboard_empresa'))
            else:
                flash('CNPJ ou senha incorretos', 'error')
        except Exception as e:
            print(f"Erro no login: {e}")
            flash('Erro interno do sistema. Tente novamente.', 'error')
        finally:
            conn.close()

    return render_template('login_empresa.html')


@app.route('/cadastro_empresa', methods=['GET', 'POST'])
def cadastro_empresa():
    if request.method == 'POST':
        nome = request.form['nome']
        email = request.form['email']
        senha = request.form['senha']
        cnpj = request.form['cnpj']
        endereco = request.form.get('endereco', '')
        cidade = request.form.get('cidade', '')
        estado = request.form.get('estado', '')
        cep = request.form.get('cep', '')

        conn = sqlite3.connect('recrutamento.db')
        cursor = conn.cursor()

        try:
            cursor.execute(
                '''INSERT INTO empresas (nome, email, senha_hash, cnpj, endereco, cidade, estado, cep)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                (nome, email, generate_password_hash(senha), cnpj, endereco,
                 cidade, estado, cep))
            conn.commit()
            flash('Empresa cadastrada com sucesso!', 'success')
            return redirect(url_for('login_empresa'))
        except sqlite3.IntegrityError:
            flash('Email já cadastrado', 'error')
        finally:
            conn.close()

    return render_template('cadastro_empresa.html')


@app.route('/login_candidato', methods=['GET', 'POST'])
@app.route('/index.html', methods=['GET', 'POST'])
def login_candidato():
    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['senha']

        conn = sqlite3.connect('recrutamento.db')
        cursor = conn.cursor()

        cursor.execute('SELECT id, senha_hash FROM candidatos WHERE email = ?',
                       (email, ))
        candidato = cursor.fetchone()
        conn.close()

        if candidato and check_password_hash(candidato[1], senha):
            session['candidato_id'] = candidato[0]
            session['tipo_usuario'] = 'candidato'
            return redirect(url_for('dashboard_candidato'))
        else:
            flash('Email ou senha incorretos', 'error')

    return render_template('login_candidato.html')


@app.route('/cadastro_candidato', methods=['GET', 'POST'])
def cadastro_candidato():
    if request.method == 'POST':
        nome = request.form['nome']
        email = request.form['email']
        senha = request.form['senha']
        telefone = request.form['telefone']
        linkedin = request.form['linkedin']
        endereco_completo = request.form['endereco_completo']
        pretensao_salarial = float(request.form['pretensao_salarial'])

        conn = sqlite3.connect('recrutamento.db')
        cursor = conn.cursor()

        try:
            cursor.execute(
                '''INSERT INTO candidatos (nome, email, senha_hash, telefone, linkedin, endereco_completo, pretensao_salarial)
                   VALUES (?, ?, ?, ?, ?, ?, ?)''',
                (nome, email, generate_password_hash(senha), telefone,
                 linkedin, endereco_completo, pretensao_salarial))
            conn.commit()
            flash('Candidato cadastrado com sucesso!', 'success')
            return redirect(url_for('login_candidato'))
        except sqlite3.IntegrityError:
            flash('Email já cadastrado', 'error')
        finally:
            conn.close()

    return render_template('cadastro_candidato.html')


@app.route('/dashboard_empresa')
def dashboard_empresa():
    if 'empresa_id' not in session or session.get('tipo_usuario') != 'empresa':
        flash('Faça login para acessar esta página', 'error')
        return redirect(url_for('login_empresa'))

    conn = sqlite3.connect('recrutamento.db')
    cursor = conn.cursor()

    cursor.execute(
        '''SELECT v.*, 
               COUNT(ca.id) as total_candidatos,
               COUNT(CASE WHEN ca.score >= 80 THEN 1 END) as candidatos_80_plus,
               COUNT(CASE WHEN ca.score >= 60 AND ca.score < 80 THEN 1 END) as candidatos_60_79,
               COUNT(CASE WHEN ca.score < 60 THEN 1 END) as candidatos_abaixo_60,
               c.nome as candidato_contratado_nome,
               ca_contratado.posicao as candidato_contratado_posicao
           FROM vagas v
           LEFT JOIN candidaturas ca ON v.id = ca.vaga_id
           LEFT JOIN candidatos c ON v.candidato_selecionado_id = c.id
           LEFT JOIN candidaturas ca_contratado ON v.candidato_selecionado_id = ca_contratado.candidato_id AND v.id = ca_contratado.vaga_id
           WHERE v.empresa_id = ?
           GROUP BY v.id
           ORDER BY v.data_criacao DESC''', (session['empresa_id'], ))

    vagas_com_stats = cursor.fetchall()
    conn.close()

    vagas_processadas = []
    for vaga in vagas_com_stats:
        # Verificar se data_criacao é timestamp ou string
        if isinstance(vaga[6], str):
            # Se for string, tentar converter para datetime
            try:
                data_criacao = datetime.strptime(
                    vaga[6], '%Y-%m-%d %H:%M:%S').strftime('%d/%m/%Y')
            except:
                data_criacao = vaga[6][:10] if vaga[
                    6] else 'N/A'  # Pegar apenas a data
        else:
            # Se for timestamp
            data_criacao = datetime.utcfromtimestamp(
                vaga[6]).strftime('%d/%m/%Y') if vaga[6] else 'N/A'

        vaga_dict = {
            'id':
            vaga[0],
            'empresa_id':
            vaga[1],
            'titulo':
            vaga[2],
            'descricao':
            vaga[3],
            'requisitos':
            vaga[4],
            'salario_oferecido':
            vaga[5],
            'diferenciais':
            vaga[11] if len(vaga) > 11 and vaga[11] else '',
            'tipo_vaga':
            vaga[7] if vaga[7] else 'Presencial',
            'endereco_vaga':
            vaga[8] if vaga[8] else '',
            'status':
            vaga[9] if vaga[9] else 'Ativa',
            'candidato_selecionado_id':
            vaga[10],
            'data_criacao':
            data_criacao,
            'total_candidatos':
            int(vaga[12]) if len(vaga) > 12 and vaga[12] is not None else 0,
            'candidatos_80_plus':
            int(vaga[13]) if len(vaga) > 13 and vaga[13] is not None else 0,
            'candidatos_60_79':
            int(vaga[14]) if len(vaga) > 14 and vaga[14] is not None else 0,
            'candidatos_abaixo_60':
            int(vaga[15]) if len(vaga) > 15 and vaga[15] is not None else 0,
            'candidato_contratado': {
                'nome': vaga[16] if len(vaga) > 16 and vaga[16] else None,
                'posicao': vaga[17] if len(vaga) > 17 and vaga[17] else None
            } if vaga[9] == 'Concluída' else None,
            'data_contratacao':
            data_criacao if vaga[9] == 'Concluída' else None,
            'feedback_ia':
            gerar_feedback_ia_vaga(
                vaga[12] if len(vaga) > 12 and vaga[12] is not None else 0,
                vaga[13] if len(vaga) > 13 and vaga[13] is not None else 0,
                vaga[14] if len(vaga) > 14 and vaga[14] is not None else 0,
                vaga[15] if len(vaga) > 15 and vaga[15] is not None else 0)
        }
        vagas_processadas.append(vaga_dict)

    return render_template('dashboard_empresa.html', vagas=vagas_processadas)


from flask import render_template, request, redirect, url_for, session, flash
from datetime import datetime
import sqlite3


@app.route('/criar_vaga', methods=['GET', 'POST'])
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

        # Novos campos
        categoria_id = request.form.get('categoria_id') or None
        nova_categoria = request.form.get('nova_categoria', '').strip()
        urgencia_contratacao = request.form.get('urgencia_contratacao', '')
        data_congelamento_agendado = request.form.get(
            'data_congelamento_agendado') or None
        usar_endereco_empresa = 'usar_endereco_empresa' in request.form

        # Campos de localização
        localizacao_endereco = request.form.get('localizacao_endereco', '')
        localizacao_cidade = request.form.get('localizacao_cidade', '')
        localizacao_estado = request.form.get('localizacao_estado', '')
        localizacao_cep = request.form.get('localizacao_cep', '')

        conn = sqlite3.connect('recrutamento.db')
        cursor = conn.cursor()

        try:
            # Criar nova categoria, se aplicável
            if nova_categoria and (not categoria_id or categoria_id == 'nova'):
                cursor.execute(
                    'INSERT OR IGNORE INTO categorias (nome) VALUES (?)',
                    (nova_categoria, ))
                cursor.execute('SELECT id FROM categorias WHERE nome = ?',
                               (nova_categoria, ))
                categoria_result = cursor.fetchone()
                if categoria_result:
                    categoria_id = categoria_result[0]

            # Buscar endereço da empresa, se solicitado
            if usar_endereco_empresa:
                cursor.execute(
                    'SELECT endereco, cidade, estado, cep FROM empresas WHERE id = ?',
                    (session['empresa_id'], ))
                endereco_empresa = cursor.fetchone()
                if endereco_empresa:
                    localizacao_endereco = endereco_empresa[
                        0] or localizacao_endereco
                    localizacao_cidade = endereco_empresa[
                        1] or localizacao_cidade
                    localizacao_estado = endereco_empresa[
                        2] or localizacao_estado
                    localizacao_cep = endereco_empresa[3] or localizacao_cep

            # Validar data de congelamento agendado
            if data_congelamento_agendado:
                try:
                    congelamento_date = datetime.strptime(
                        data_congelamento_agendado, '%Y-%m-%d')
                    if congelamento_date <= datetime.now():
                        flash(
                            'A data de congelamento precisa ser uma data futura.',
                            'error')
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
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Ativa', ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (titulo, descricao, requisitos, salario_oferecido, tipo_vaga,
                  diferenciais, session['empresa_id'],
                  datetime.now().strftime('%Y-%m-%d %H:%M:%S'), categoria_id,
                  urgencia_contratacao, data_congelamento_agendado,
                  int(usar_endereco_empresa), localizacao_endereco,
                  localizacao_cidade, localizacao_estado, localizacao_cep))

            conn.commit()
            flash('Vaga criada com sucesso!', 'success')
            return redirect(url_for('dashboard_empresa'))

        except Exception as e:
            flash(f'Erro ao criar vaga: {str(e)}', 'error')
            print(f"Erro detalhado: {e}")
        finally:
            conn.close()

    # GET: renderizar formulário
    conn = sqlite3.connect('recrutamento.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, nome FROM categorias ORDER BY nome')
    categorias = [{'id': row[0], 'nome': row[1]} for row in cursor.fetchall()]
    conn.close()

    hoje = datetime.now().strftime('%Y-%m-%d')  # usado no min do input de data

    return render_template('criar_vaga.html', categorias=categorias, hoje=hoje)


@app.route('/candidatos_vaga/<int:vaga_id>')
def candidatos_vaga(vaga_id):
    if 'empresa_id' not in session:
        return redirect(url_for('login_empresa'))

    conn = sqlite3.connect('recrutamento.db')
    cursor = conn.cursor()

    cursor.execute(
        '''SELECT c.nome, c.email, c.telefone, c.linkedin, ca.score, ca.posicao, c.id, c.endereco_completo
           FROM candidaturas ca
           JOIN candidatos c ON ca.candidato_id = c.id
           WHERE ca.vaga_id = ?
           ORDER BY ca.score DESC''', (vaga_id, ))

    candidatos = cursor.fetchall()

    cursor.execute('SELECT titulo FROM vagas WHERE id = ?', (vaga_id, ))
    vaga = cursor.fetchone()
    conn.close()

    return render_template('candidatos_vaga.html',
                           candidatos=candidatos,
                           vaga_titulo=vaga[0] if vaga else '',
                           vaga_id=vaga_id)


@app.route('/dashboard_candidato')
def dashboard_candidato():
    if 'candidato_id' not in session:
        return redirect(url_for('login_candidato'))

    conn = sqlite3.connect('recrutamento.db')
    cursor = conn.cursor()

    # Verifica se o candidato já enviou currículo
    cursor.execute('SELECT texto_curriculo FROM candidatos WHERE id = ?',
                   (session['candidato_id'], ))
    candidato = cursor.fetchone()

    if not candidato or not candidato[0]:
        conn.close()
        return redirect(url_for('upload_curriculo'))

    # Candidaturas em vagas ATIVAS, ordenadas por score decrescente
    cursor.execute(
        '''
        SELECT v.id, v.titulo, e.nome AS empresa_nome, v.salario_oferecido, ca.score, ca.posicao,
               CASE WHEN cvf.id IS NOT NULL THEN 1 ELSE 0 END as is_favorita
        FROM candidaturas ca
        JOIN vagas v ON ca.vaga_id = v.id
        JOIN empresas e ON v.empresa_id = e.id
        LEFT JOIN candidato_vaga_favorita cvf ON cvf.candidato_id = ? AND cvf.vaga_id = v.id
        WHERE ca.candidato_id = ? AND v.status = 'Ativa'
        ORDER BY ca.score DESC
        ''', (session['candidato_id'], session['candidato_id']))
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
        '''
        SELECT v.id, v.titulo, v.descricao, v.requisitos, v.salario_oferecido, 
               e.nome as empresa_nome, v.diferenciais, v.tipo_vaga, v.endereco_vaga,
               CASE WHEN cvf.id IS NOT NULL THEN 1 ELSE 0 END as is_favorita
        FROM vagas v
        JOIN empresas e ON v.empresa_id = e.id
        LEFT JOIN candidato_vaga_favorita cvf ON cvf.candidato_id = ? AND cvf.vaga_id = v.id
        WHERE v.id NOT IN (
            SELECT vaga_id FROM candidaturas WHERE candidato_id = ?
        ) AND v.status = 'Ativa'
        ''', (session['candidato_id'], session['candidato_id']))
    vagas_disponiveis = cursor.fetchall()

    # Buscar vagas favoritas (com e sem candidatura)
    cursor.execute(
        '''
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
        ''', (session['candidato_id'], session['candidato_id']))
    vagas_favoritas = cursor.fetchall()

    # Informações do candidato
    cursor.execute(
        'SELECT pretensao_salarial, texto_curriculo, endereco_completo FROM candidatos WHERE id = ?',
        (session['candidato_id'], ))
    candidato_info = cursor.fetchone()

    conn.close()

    # Calcula score para vagas disponíveis
    avaliador = criar_avaliador(MODO_IA)
    vagas_com_score = []
    for vaga in vagas_disponiveis:
        score = avaliador.calcular_score(
            candidato_info[1], vaga[3], candidato_info[0], vaga[4],
            vaga[6] if vaga[6] else '',
            candidato_info[2] if len(candidato_info) > 2 else None, vaga[8],
            vaga[7])
        vaga_processada = (int(vaga[0]), vaga[1], vaga[2], vaga[3],
                           float(vaga[4]) if vaga[4] else 0.0, vaga[5], vaga[6]
                           or '', vaga[7] or 'Presencial', vaga[8]
                           or '', float(score), bool(vaga[9]))
        vagas_com_score.append(vaga_processada)

    # Processa vagas favoritas
    vagas_favoritas_processadas = []
    for vaga in vagas_favoritas:
        if not vaga[9]:  # Se não se candidatou ainda, calcular score
            score = avaliador.calcular_score(
                candidato_info[1], vaga[3], candidato_info[0], vaga[4],
                vaga[6] if vaga[6] else '',
                candidato_info[2] if len(candidato_info) > 2 else None,
                vaga[8], vaga[7])
        else:
            score = vaga[10]  # Score já existente da candidatura

        vaga_processada = {
            'id': int(vaga[0]),
            'titulo': vaga[1],
            'descricao': vaga[2],
            'requisitos': vaga[3],
            'salario': float(vaga[4]) if vaga[4] else 0.0,
            'empresa_nome': vaga[5],
            'diferenciais': vaga[6] or '',
            'tipo_vaga': vaga[7] or 'Presencial',
            'endereco_vaga': vaga[8] or '',
            'ja_candidatou': bool(vaga[9]),
            'score': float(score) if score else 0.0,
            'posicao': int(vaga[11]) if vaga[11] else None,
            'is_favorita': True
        }
        vagas_favoritas_processadas.append(vaga_processada)

    # Ordena pelas melhores recomendações
    vagas_com_score.sort(key=lambda x: x[9], reverse=True)
    top_vagas = vagas_com_score[:TOP_JOBS]

    return render_template('dashboard_candidato.html',
                           vagas_recomendadas=top_vagas,
                           vagas_candidatadas=vagas_candidatadas,
                           vagas_favoritas=vagas_favoritas_processadas)


@app.route('/upload_curriculo', methods=['GET', 'POST'])
def upload_curriculo():
    if 'candidato_id' not in session:
        return redirect(url_for('login_candidato'))

    if request.method == 'POST':
        resultado = processar_upload_curriculo(request,
                                               session['candidato_id'])

        # Processar mensagens corretamente
        for mensagem in resultado['mensagens']:
            if isinstance(mensagem, dict) and 'texto' in mensagem:
                flash(mensagem['texto'], mensagem.get('tipo', 'info'))
            else:
                flash(str(mensagem), 'info')

        if resultado['sucesso']:
            return render_template(
                'processar_curriculo.html',
                dados_extraidos=resultado['dados_extraidos'])
        else:
            return redirect(request.url)

    return render_template('upload_curriculo.html')


@app.route('/finalizar_curriculo', methods=['POST'])
def finalizar_curriculo():
    if 'candidato_id' not in session:
        return redirect(url_for('login_candidato'))

    resultado = finalizar_processamento_curriculo(request,
                                                  session['candidato_id'])

    # Processar mensagens corretamente
    for mensagem in resultado['mensagens']:
        if isinstance(mensagem, dict) and 'texto' in mensagem:
            flash(mensagem['texto'], mensagem.get('tipo', 'info'))
        else:
            flash(str(mensagem), 'info')

    if resultado['sucesso']:
        return redirect(url_for('dashboard_candidato'))
    else:
        return redirect(url_for('upload_curriculo'))


@app.route('/candidatar/<int:vaga_id>')
def candidatar(vaga_id):
    if 'candidato_id' not in session:
        return redirect(url_for('login_candidato'))

    from utils.helpers import processar_candidatura
    resultado = processar_candidatura(session['candidato_id'], vaga_id,
                                      MODO_IA)

    # Processar mensagens para garantir que estão em formato correto
    for mensagem in resultado['mensagens']:
        if isinstance(mensagem, dict) and 'texto' in mensagem:
            flash(mensagem['texto'], mensagem.get('tipo', 'info'))
        else:
            flash(str(mensagem), 'info')

    return redirect(url_for('dashboard_candidato'))


@app.route('/api/candidatos_vaga/<int:vaga_id>')
def api_candidatos_vaga(vaga_id):
    if 'empresa_id' not in session:
        return jsonify({'error': 'Não autorizado'}), 401

    conn = sqlite3.connect('recrutamento.db')
    cursor = conn.cursor()

    cursor.execute(
        '''SELECT c.id, c.nome, ca.score
           FROM candidaturas ca
           JOIN candidatos c ON ca.candidato_id = c.id
           JOIN vagas v ON ca.vaga_id = v.id
           WHERE ca.vaga_id = ? AND v.empresa_id = ?
           ORDER BY ca.score DESC''', (vaga_id, session['empresa_id']))

    candidatos = cursor.fetchall()
    conn.close()

    return jsonify([{
        'id': c[0],
        'nome': c[1],
        'score': round(c[2], 1)
    } for c in candidatos])


# Função para enviar e-mail (compatibilidade)
def enviar_email(destinatario, assunto, corpo):
    return notification_system.enviar_email(destinatario, assunto, corpo)


@app.route('/encerrar_vaga', methods=['POST'])
def encerrar_vaga():
    if 'empresa_id' not in session:
        return jsonify({'error': 'Não autorizado'}), 401

    data = request.get_json()
    vaga_id = data.get('vaga_id')
    acao = data.get('acao')
    candidato_id = data.get('candidato_id')
    mensagem_personalizada = data.get('mensagem_personalizada', '')

    if not vaga_id or not acao:
        return jsonify({'error': 'Dados incompletos'}), 400

    conn = sqlite3.connect('recrutamento.db')
    cursor = conn.cursor()

    # Verificar se a vaga pertence à empresa
    cursor.execute('SELECT titulo FROM vagas WHERE id = ? AND empresa_id = ?',
                   (vaga_id, session['empresa_id']))
    vaga_info = cursor.fetchone()
    if not vaga_info:
        conn.close()
        return jsonify({'error': 'Vaga não encontrada'}), 404

    vaga_titulo = vaga_info[0]

    try:
        # Buscar candidatos da vaga
        cursor.execute(
            'SELECT candidato_id FROM candidaturas WHERE vaga_id = ?',
            (vaga_id, ))
        todos_candidatos = [row[0] for row in cursor.fetchall()]

        if acao == 'contratar':
            if not candidato_id:
                return jsonify({'error': 'Candidato não selecionado'}), 400

            cursor.execute(
                'SELECT id FROM candidaturas WHERE candidato_id = ? AND vaga_id = ?',
                (candidato_id, vaga_id))
            if not cursor.fetchone():
                return jsonify(
                    {'error': 'Candidato não se candidatou a esta vaga'}), 400

            # Atualizar vaga como concluída
            cursor.execute(
                '''UPDATE vagas 
                   SET status = "Concluída", candidato_selecionado_id = ? 
                   WHERE id = ?''', (candidato_id, vaga_id))

            # Notificar candidato contratado
            notification_system.notificar_contratacao(candidato_id, vaga_id,
                                                      session['empresa_id'],
                                                      mensagem_personalizada)

            # Notificar outros candidatos
            for cid in todos_candidatos:
                if cid != candidato_id:
                    msg = f"A vaga '{vaga_titulo}' foi concluída. Outro candidato foi selecionado."
                    notification_system.criar_notificacao(
                        cid, msg, vaga_id, session['empresa_id'],
                        'vaga_concluida')

                    cursor.execute('SELECT email FROM candidatos WHERE id = ?',
                                   (cid, ))
                    email_result = cursor.fetchone()
                    if email_result:
                        notification_system.enviar_email(
                            email_result[0], f"Vaga Concluída - {vaga_titulo}",
                            msg)

            response = {
                'success': True,
                'message': 'Candidato contratado com sucesso!'
            }

        elif acao == 'congelar':
            cursor.execute(
                'UPDATE vagas SET status = "Congelada" WHERE id = ?',
                (vaga_id, ))
            notification_system.notificar_vaga_congelada(vaga_id)
            response = {
                'success': True,
                'message': 'Vaga congelada com sucesso!'
            }

        elif acao == 'excluir':
            # Notificar antes de excluir
            notification_system.notificar_vaga_excluida(vaga_id)

            # Excluir candidaturas e vaga
            cursor.execute('DELETE FROM candidaturas WHERE vaga_id = ?',
                           (vaga_id, ))
            cursor.execute('DELETE FROM vagas WHERE id = ?', (vaga_id, ))
            response = {
                'success': True,
                'message': 'Vaga excluída com sucesso!'
            }

        elif acao == 'reativar':
            cursor.execute('UPDATE vagas SET status = "Ativa" WHERE id = ?',
                           (vaga_id, ))

            # Notificar candidatos sobre reativação
            for cid in todos_candidatos:
                msg = f"Boa notícia! A vaga '{vaga_titulo}' foi reativada. Sua candidatura continua válida e o processo seletivo foi retomado."
                notification_system.criar_notificacao(cid, msg, vaga_id,
                                                      session['empresa_id'],
                                                      'vaga_reativada')

                cursor.execute('SELECT email FROM candidatos WHERE id = ?',
                               (cid, ))
                email_result = cursor.fetchone()
                if email_result:
                    notification_system.enviar_email(
                        email_result[0], f"Vaga Reativada - {vaga_titulo}",
                        msg)

            response = {
                'success': True,
                'message': 'Vaga reativada com sucesso!'
            }

        else:
            return jsonify({'error': 'Ação inválida'}), 400

        conn.commit()
        return jsonify(response)

    except Exception as e:
        conn.rollback()
        print(f"Erro ao encerrar vaga: {e}")
        return jsonify({'error': f'Erro ao processar ação: {str(e)}'}), 500
    finally:
        conn.close()


@app.route('/editar_perfil_candidato', methods=['GET', 'POST'])
def editar_perfil_candidato():
    if 'candidato_id' not in session:
        return redirect(url_for('login_candidato'))

    conn = sqlite3.connect('recrutamento.db')
    cursor = conn.cursor()

    if request.method == 'POST':
        nome = request.form['nome']
        telefone = request.form['telefone']
        linkedin = request.form['linkedin']
        pretensao_salarial = float(request.form['pretensao_salarial'])
        experiencia = request.form['experiencia']
        competencias = request.form['competencias']
        resumo_profissional = request.form['resumo_profissional']

        cursor.execute(
            '''
            UPDATE candidatos 
            SET nome = ?, telefone = ?, linkedin = ?, pretensao_salarial = ?,
                experiencia = ?, competencias = ?, resumo_profissional = ?
            WHERE id = ?
        ''', (nome, telefone, linkedin, pretensao_salarial, experiencia,
              competencias, resumo_profissional, session['candidato_id']))

        conn.commit()
        conn.close()

        flash('Perfil atualizado com sucesso!', 'success')
        return redirect(url_for('dashboard_candidato'))

    cursor.execute(
        '''
        SELECT nome, telefone, linkedin, pretensao_salarial, 
               experiencia, competencias, resumo_profissional
        FROM candidatos WHERE id = ?
    ''', (session['candidato_id'], ))

    candidato = cursor.fetchone()
    conn.close()

    return render_template('editar_perfil_candidato.html', candidato=candidato)


@app.route('/editar_vaga/<int:vaga_id>', methods=['GET', 'POST'])
def editar_vaga(vaga_id):
    if 'empresa_id' not in session:
        flash('Acesso negado', 'error')
        return redirect(url_for('login_empresa'))

    conn = sqlite3.connect('recrutamento.db')
    cursor = conn.cursor()

    if request.method == 'POST':
        titulo = request.form['titulo']
        descricao = request.form['descricao']
        requisitos = request.form['requisitos']
        salario_oferecido = float(request.form['salario_oferecido'])
        tipo_vaga = request.form['tipo_vaga']
        diferenciais = request.form.get('diferenciais', '')

        # Novos campos
        categoria_id = request.form.get('categoria_id') or None
        nova_categoria = request.form.get('nova_categoria', '').strip()
        urgencia_contratacao = request.form.get('urgencia_contratacao', '')
        data_congelamento_agendado = request.form.get(
            'data_congelamento_agendado') or None
        usar_endereco_empresa = 'usar_endereco_empresa' in request.form

        # Campos de localização
        localizacao_endereco = request.form.get('localizacao_endereco', '')
        localizacao_cidade = request.form.get('localizacao_cidade', '')
        localizacao_estado = request.form.get('localizacao_estado', '')
        localizacao_cep = request.form.get('localizacao_cep', '')

        try:
            # Se nova categoria foi informada, criar/buscar categoria
            if nova_categoria and (not categoria_id or categoria_id == 'nova'):
                cursor.execute(
                    'INSERT OR IGNORE INTO categorias (nome) VALUES (?)',
                    (nova_categoria, ))
                cursor.execute('SELECT id FROM categorias WHERE nome = ?',
                               (nova_categoria, ))
                categoria_result = cursor.fetchone()
                if categoria_result:
                    categoria_id = categoria_result[0]

            # Se usar endereço da empresa, buscar dados da empresa
            if usar_endereco_empresa:
                cursor.execute(
                    'SELECT endereco, cidade, estado, cep FROM empresas WHERE id = ?',
                    (session['empresa_id'], ))
                endereco_empresa = cursor.fetchone()
                if endereco_empresa:
                    localizacao_endereco = endereco_empresa[
                        0] or localizacao_endereco
                    localizacao_cidade = endereco_empresa[
                        1] or localizacao_cidade
                    localizacao_estado = endereco_empresa[
                        2] or localizacao_estado
                    localizacao_cep = endereco_empresa[3] or localizacao_cep

            cursor.execute(
                '''
                UPDATE vagas 
                SET titulo = ?, descricao = ?, requisitos = ?, salario_oferecido = ?, tipo_vaga = ?, diferenciais = ?,
                    categoria_id = ?, urgencia_contratacao = ?, data_congelamento_agendado = ?, usar_endereco_empresa = ?,
                    localizacao_endereco = ?, localizacao_cidade = ?, localizacao_estado = ?, localizacao_cep = ?
                WHERE id = ?
            ''', (titulo, descricao, requisitos, salario_oferecido, tipo_vaga,
                  diferenciais, categoria_id, urgencia_contratacao,
                  data_congelamento_agendado, usar_endereco_empresa,
                  localizacao_endereco, localizacao_cidade, localizacao_estado,
                  localizacao_cep, vaga_id))

            conn.commit()
            flash('Vaga atualizada com sucesso!', 'success')

            # Notificar candidatos sobre alteração da vaga
            from utils.notifications import notificar_alteracao_vaga
            notificar_alteracao_vaga(vaga_id, 'atualizada')

            return redirect(url_for('dashboard_empresa'))

        except Exception as e:
            flash(f'Erro ao atualizar vaga: {str(e)}', 'error')
            print(f"Erro detalhado: {e}")

    # Buscar dados da vaga para exibição (funciona tanto para GET quanto para POST com erro)
    cursor.execute(
        '''
        SELECT v.*, c.nome as categoria_nome
        FROM vagas v
        LEFT JOIN categorias c ON v.categoria_id = c.id
        WHERE v.id = ?
    ''', (vaga_id, ))
    vaga_completa = cursor.fetchone()

    if vaga_completa:
        colunas = [desc[0] for desc in cursor.description]
        vaga = dict(zip(colunas, vaga_completa))
    else:
        vaga = {}
        flash('Vaga não encontrada', 'error')
        return redirect(url_for('dashboard_empresa'))

    # Buscar categorias para o formulário
    cursor.execute('SELECT id, nome FROM categorias ORDER BY nome')
    categorias = [{'id': row[0], 'nome': row[1]} for row in cursor.fetchall()]

    conn.close()

    return render_template('editar_vaga.html',
                           vaga=vaga,
                           categorias=categorias,
                           datetime=datetime,
                           timedelta=timedelta)


@app.route('/vaga/<int:vaga_id>')
def detalhes_vaga(vaga_id):
    if 'candidato_id' not in session:
        return redirect(url_for('login_candidato'))

    conn = sqlite3.connect('recrutamento.db')
    cursor = conn.cursor()

    # Buscar dados da vaga e empresa
    cursor.execute(
        '''
        SELECT v.*, e.nome as empresa_nome
        FROM vagas v
        JOIN empresas e ON v.empresa_id = e.id
        WHERE v.id = ? AND v.status = 'Ativa'
    ''', (vaga_id, ))

    vaga_data = cursor.fetchone()

    if not vaga_data:
        flash('Vaga não encontrada ou não está mais ativa', 'error')
        return redirect(url_for('dashboard_candidato'))

    # Verificar se já se candidatou
    cursor.execute(
        '''
        SELECT id, score FROM candidaturas 
        WHERE candidato_id = ? AND vaga_id = ?
    ''', (session['candidato_id'], vaga_id))
    candidatura = cursor.fetchone()

    # Buscar dados do candidato para calcular feedback
    cursor.execute(
        '''
        SELECT texto_curriculo, endereco_completo, pretensao_salarial
        FROM candidatos WHERE id = ?
    ''', (session['candidato_id'], ))
    candidato_data = cursor.fetchone()

    conn.close()

    # Estruturar dados da vaga
    vaga = {
        'id':
        vaga_data[0],
        'titulo':
        vaga_data[2],
        'descricao':
        vaga_data[3],
        'requisitos':
        vaga_data[4],
        'salario_oferecido':
        vaga_data[5],
        'tipo_vaga':
        vaga_data[7] or 'Presencial',
        'endereco_vaga':
        vaga_data[8],
        'diferenciais':
        vaga_data[11],
        'data_criacao':
        datetime.strptime(vaga_data[6], '%Y-%m-%d %H:%M:%S')
        if vaga_data[6] else None
    }

    empresa = {'nome': vaga_data[12]}

    # Calcular score e feedback se não candidatado ainda
    score = None
    feedback_performance = None

    if candidato_data:
        from avaliador import criar_avaliador
        avaliador = criar_avaliador(MODO_IA)

        score = candidatura[1] if candidatura else avaliador.calcular_score(
            candidato_data[0], vaga['requisitos'], candidato_data[2],
            vaga['salario_oferecido'], vaga['diferenciais'], candidato_data[1],
            vaga['endereco_vaga'], vaga['tipo_vaga'])

        # Gerar feedback de performance
        feedback_performance = {
            'requisitos_atendidos':
            len([
                r for r in avaliador._extrair_palavras_chave(
                    vaga['requisitos'].lower())
                if r in candidato_data[0].lower()
            ]),
            'total_requisitos':
            len(avaliador._extrair_palavras_chave(vaga['requisitos'].lower())),
            'diferenciais_atendidos':
            len([
                d for d in avaliador._extrair_palavras_chave(
                    vaga['diferenciais'].lower(
                    ) if vaga['diferenciais'] else '')
                if d in candidato_data[0].lower()
            ]) if vaga['diferenciais'] else 0,
            'bonus_localizacao':
            bool(vaga['tipo_vaga'] in ['Presencial', 'Híbrida']
                 and candidato_data[1] and vaga['endereco_vaga'])
        }

    return render_template('detalhes_vaga.html',
                           vaga=vaga,
                           empresa=empresa,
                           score=score,
                           feedback_performance=feedback_performance,
                           ja_candidatado=bool(candidatura))


@app.route('/minhas_candidaturas')
def minhas_candidaturas():
    if 'candidato_id' not in session:
        return redirect(url_for('login_candidato'))

    conn = sqlite3.connect('recrutamento.db')
    cursor = conn.cursor()

    cursor.execute(
        '''
        SELECT v.id, v.titulo, e.nome as empresa_nome, v.salario_oferecido,
               ca.score, ca.posicao, ca.data_candidatura
        FROM candidaturas ca
        JOIN vagas v ON ca.vaga_id = v.id
        JOIN empresas e ON v.empresa_id = e.id
        WHERE ca.candidato_id = ?
        ORDER BY ca.data_candidatura DESC
    ''', (session['candidato_id'], ))

    candidaturas = cursor.fetchall()
    conn.close()

    return render_template('minhas_candidaturas.html',
                           candidaturas=candidaturas)


@app.route('/baixar_curriculo/<int:candidato_id>')
def baixar_curriculo(candidato_id):
    if 'empresa_id' not in session:
        return redirect(url_for('login_empresa'))

    conn = sqlite3.connect('recrutamento.db')
    cursor = conn.cursor()

    # Verificar se a empresa tem acesso ao candidato (através de candidatura)
    cursor.execute(
        '''
        SELECT COUNT(*) FROM candidaturas ca
        JOIN vagas v ON ca.vaga_id = v.id
        WHERE ca.candidato_id = ? AND v.empresa_id = ?
    ''', (candidato_id, session['empresa_id']))

    if cursor.fetchone()[0] == 0:
        flash('Acesso negado ao currículo', 'error')
        return redirect(url_for('dashboard_empresa'))

    # Buscar dados do candidato
    cursor.execute(
        '''
        SELECT nome, caminho_curriculo
        FROM candidatos WHERE id = ?
    ''', (candidato_id, ))

    candidato = cursor.fetchone()
    conn.close()

    if not candidato:
        flash('Candidato não encontrado', 'error')
        return redirect(url_for('dashboard_empresa'))

    # Verificar se o arquivo do currículo existe
    if not candidato[1]:
        flash('Currículo não disponível para download', 'error')
        return redirect(url_for('dashboard_empresa'))

    caminho_curriculo = os.path.join('uploads', candidato[1])

    if not os.path.exists(caminho_curriculo):
        flash('Arquivo do currículo não encontrado', 'error')
        return redirect(url_for('dashboard_empresa'))

    nome_download = f"curriculo_{candidato[0].replace(' ', '_')}.pdf"

    return send_file(caminho_curriculo,
                     as_attachment=True,
                     download_name=nome_download,
                     mimetype='application/pdf')


@app.route('/empresa/relatorio')
def relatorio_empresa():
    if 'empresa_id' not in session:
        flash('Faça login para acessar essa página', 'error')
        return redirect(url_for('login_empresa'))

    empresa_id = session['empresa_id']

    # Buscar vagas da empresa para o filtro
    conn = sqlite3.connect('recrutamento.db')
    cursor = conn.cursor()
    cursor.execute(
        'SELECT id, titulo FROM vagas WHERE empresa_id = ? ORDER BY titulo',
        (empresa_id, ))
    vagas_disponiveis = cursor.fetchall()
    conn.close()

    from utils.relatorio_generator import gerar_dados_graficos
    dados_graficos = gerar_dados_graficos(empresa_id)

    return render_template('relatorio_empresa.html',
                           vagas_disponiveis=vagas_disponiveis,
                           dados_graficos=json.dumps(dados_graficos))


@app.route('/empresa/relatorio/completo')
def relatorio_completo():
    if 'empresa_id' not in session:
        return redirect(url_for('login_empresa'))

    empresa_id = session['empresa_id']
    filtro_vagas = request.args.getlist('vagas')

    # Se foi especificado filtro, converter para inteiros
    if filtro_vagas:
        try:
            filtro_vagas = [int(v) for v in filtro_vagas]
        except ValueError:
            filtro_vagas = None
    else:
        filtro_vagas = None

    from utils.relatorio_generator import gerar_relatorio_completo, gerar_html_relatorio

    try:
        dados = gerar_relatorio_completo(empresa_id, filtro_vagas)
        html_relatorio = gerar_html_relatorio(dados)

        return html_relatorio

    except Exception as e:
        flash(f'Erro ao gerar relatório: {str(e)}', 'error')
        return redirect(url_for('relatorio_empresa'))


@app.route('/api/relatorio/graficos')
def api_relatorio_graficos():
    if 'empresa_id' not in session:
        return {'error': 'Não autorizado'}, 401

    empresa_id = session['empresa_id']
    filtro_vagas = request.args.getlist('vagas')

    if filtro_vagas:
        try:
            filtro_vagas = [int(v) for v in filtro_vagas]
        except ValueError:
            filtro_vagas = None
    else:
        filtro_vagas = None

    from utils.relatorio_generator import gerar_dados_graficos

    try:
        dados = gerar_dados_graficos(empresa_id, filtro_vagas)
        return dados
    except Exception as e:
        return {'error': str(e)}, 500


@app.route('/cancelar_candidatura', methods=['POST'])
def cancelar_candidatura():
    if 'candidato_id' not in session:
        return jsonify({'error': 'Não autorizado'}), 401

    data = request.get_json()
    vaga_id = data.get('vaga_id')

    conn = sqlite3.connect('recrutamento.db')
    cursor = conn.cursor()

    # Verificar se a candidatura existe
    cursor.execute(
        'SELECT id FROM candidaturas WHERE candidato_id = ? AND vaga_id = ?',
        (session['candidato_id'], vaga_id))
    candidatura = cursor.fetchone()

    if not candidatura:
        conn.close()
        return {'error': 'Candidatura não encontrada'}, 404

    # Remover candidatura
    cursor.execute(
        'DELETE FROM candidaturas WHERE candidato_id = ? AND vaga_id = ?',
        (session['candidato_id'], vaga_id))

    # Recalcular posições dos candidatos restantes
    cursor.execute(
        '''
        UPDATE candidaturas
        SET posicao = (
            SELECT COUNT(*) + 1
            FROM candidaturas c2
            WHERE c2.vaga_id = candidaturas.vaga_id 
            AND c2.score > candidaturas.score
        )
        WHERE vaga_id = ?
    ''', (vaga_id, ))

    conn.commit()
    conn.close()

    return {'success': True}


@app.route("/reativar_vaga/<int:vaga_id>", methods=["POST"])
def reativar_vaga_route(vaga_id):
    if 'empresa_id' not in session:
        return jsonify({'error': 'Não autorizado'}), 401

    conn = sqlite3.connect('recrutamento.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE vagas SET status = "Ativa" WHERE id = ?',
                   (vaga_id, ))
    conn.commit()
    conn.close()
    return redirect(url_for('dashboard_empresa'))


@app.route('/duplicar_vaga/<int:vaga_id>')
def duplicar_vaga(vaga_id):
    """Duplicar uma vaga existente"""
    if 'empresa_id' not in session:
        flash('Acesso negado', 'error')
        return redirect(url_for('login_empresa'))

    conn = sqlite3.connect('recrutamento.db')
    cursor = conn.cursor()

    try:
        # Buscar dados da vaga original
        cursor.execute(
            '''
            SELECT titulo, descricao, requisitos, salario_oferecido, tipo_vaga, diferenciais,
                   categoria_id, urgencia_contratacao, usar_endereco_empresa,
                   localizacao_endereco, localizacao_cidade, localizacao_estado, localizacao_cep
            FROM vagas 
            WHERE id = ? AND empresa_id = ?
        ''', (vaga_id, session['empresa_id']))

        vaga_original = cursor.fetchone()

        if not vaga_original:
            flash('Vaga não encontrada', 'error')
            return redirect(url_for('dashboard_empresa'))

        # Criar nova vaga com dados duplicados
        cursor.execute(
            '''
            INSERT INTO vagas (titulo, descricao, requisitos, salario_oferecido, tipo_vaga, diferenciais,
                             empresa_id, data_criacao, status, categoria_id, urgencia_contratacao, 
                             usar_endereco_empresa, localizacao_endereco, localizacao_cidade, 
                             localizacao_estado, localizacao_cep)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Ativa', ?, ?, ?, ?, ?, ?, ?)
        ''', (f"[CÓPIA] {vaga_original[0]}", vaga_original[1],
              vaga_original[2], vaga_original[3],
              vaga_original[4], vaga_original[5], session['empresa_id'],
              datetime.now().strftime('%Y-%m-%d %H:%M:%S'), vaga_original[6],
              vaga_original[7], vaga_original[8], vaga_original[9],
              vaga_original[10], vaga_original[11], vaga_original[12]))

        conn.commit()
        flash('Vaga duplicada com sucesso!', 'success')

    except Exception as e:
        flash(f'Erro ao duplicar vaga: {str(e)}', 'error')
        print(f"Erro detalhado: {e}")
    finally:
        conn.close()

    return redirect(url_for('dashboard_empresa'))


@app.route('/api/notificacoes')
def api_notificacoes():
    if 'candidato_id' not in session:
        return jsonify([])

    conn = sqlite3.connect('recrutamento.db')
    cursor = conn.cursor()

    cursor.execute(
        '''
        SELECT n.id, n.vaga_id, n.empresa_id, n.mensagem, n.lida, n.data_envio,
               v.titulo AS vaga_titulo,
               e.nome AS empresa_nome
        FROM notificacoes n
        LEFT JOIN vagas v ON n.vaga_id = v.id
        LEFT JOIN empresas e ON n.empresa_id = e.id
        WHERE n.candidato_id = ?
        ORDER BY n.data_envio DESC
    ''', (session['candidato_id'], ))

    notificacoes = [{
        'id': row[0],
        'vaga_id': row[1],
        'empresa_id': row[2],
        'mensagem': row[3],
        'lida': bool(row[4]),
        'data_envio': row[5],
        'vaga_titulo': row[6],
        'empresa_nome': row[7]
    } for row in cursor.fetchall()]

    conn.close()
    return jsonify(notificacoes)


@app.route('/api/notificacoes/marcar-lida', methods=['POST'])
def marcar_notificacao_lida():
    if 'candidato_id' not in session:
        return jsonify({'error': 'Não autorizado'}), 401

    data = request.get_json()
    notificacao_id = data.get('id')

    if not notificacao_id:
        return jsonify({'error': 'ID da notificação é obrigatório'}), 400

    conn = sqlite3.connect('recrutamento.db')
    cursor = conn.cursor()

    cursor.execute(
        '''
        UPDATE notificacoes 
        SET lida = 1 
        WHERE id = ? AND candidato_id = ?
    ''', (notificacao_id, session['candidato_id']))

    conn.commit()
    conn.close()

    return jsonify({'success': True})


@app.route('/api/notificacoes/marcar-todas-lidas', methods=['POST'])
def marcar_todas_notificacoes_lidas():
    if 'candidato_id' not in session:
        return jsonify({'error': 'Não autorizado'}), 401

    conn = sqlite3.connect('recrutamento.db')
    cursor = conn.cursor()

    cursor.execute(
        '''
        UPDATE notificacoes 
        SET lida = 1 
        WHERE candidato_id = ?
    ''', (session['candidato_id'], ))

    conn.commit()
    conn.close()

    return jsonify({'success': True})


@app.route('/api/notificacoes/<int:notificacao_id>/apagar', methods=['DELETE'])
def apagar_notificacao(notificacao_id):
    if 'candidato_id' not in session:
        return jsonify({'error': 'Não autorizado'}), 401

    conn = sqlite3.connect('recrutamento.db')
    cursor = conn.cursor()

    cursor.execute(
        '''
        DELETE FROM notificacoes 
        WHERE id = ? AND candidato_id = ?
    ''', (notificacao_id, session['candidato_id']))

    conn.commit()
    sucesso = cursor.rowcount > 0
    conn.close()

    return jsonify({'success': sucesso})


@app.route('/api/notificacoes/apagar-todas', methods=['DELETE'])
def apagar_todas_notificacoes():
    if 'candidato_id' not in session:
        return jsonify({'error': 'Não autorizado'}), 401

    conn = sqlite3.connect('recrutamento.db')
    cursor = conn.cursor()

    cursor.execute(
        '''
        DELETE FROM notificacoes 
        WHERE candidato_id = ?
    ''', (session['candidato_id'], ))

    conn.commit()
    count = cursor.rowcount
    conn.close()

    return jsonify({'success': True, 'deleted_count': count})


@app.route('/politica-privacidade')
def politica_privacidade():
    from datetime import datetime
    return render_template('politica_privacidade.html',
                           data_atual=datetime.now().strftime('%B de %Y'))


@app.route('/logout')
def logout():
    session.clear()
    flash('Logout realizado com sucesso!', 'success')
    return redirect(url_for('index'))


@app.route('/empresa/endereco')
def get_endereco_empresa():
    if 'empresa_id' not in session:
        return jsonify({'error': 'Não autorizado'}), 401

    conn = sqlite3.connect('recrutamento.db')
    cursor = conn.cursor()

    try:
        cursor.execute(
            'SELECT endereco, cidade, estado, cep FROM empresas WHERE id = ?',
            (session['empresa_id'], ))
        empresa = cursor.fetchone()

        if empresa:
            return jsonify({
                'endereco': empresa[0],
                'cidade': empresa[1],
                'estado': empresa[2],
                'cep': empresa[3]
            })
        else:
            return jsonify({'error': 'Empresa não encontrada'}), 404

    finally:
        conn.close()


# =========================
# SISTEMA DE FAVORITOS
# =========================


@app.route('/api/favoritar-vaga', methods=['POST'])
def favoritar_vaga():
    """API para candidato favoritar/desfavoritar vaga"""
    if 'candidato_id' not in session:
        return jsonify({'success': False, 'message': 'Não autorizado'}), 401

    data = request.get_json()
    vaga_id = data.get('vaga_id')
    acao = data.get('acao', 'toggle')  # toggle, add, remove

    if not vaga_id:
        return jsonify({
            'success': False,
            'message': 'Vaga ID obrigatório'
        }), 400

    conn = sqlite3.connect('recrutamento.db')
    cursor = conn.cursor()

    try:
        candidato_id = session['candidato_id']

        # Verificar se já está favoritada
        cursor.execute(
            '''
            SELECT id FROM candidato_vaga_favorita 
            WHERE candidato_id = ? AND vaga_id = ?
        ''', (candidato_id, vaga_id))

        ja_favoritada = cursor.fetchone() is not None

        if acao == 'toggle' or (acao == 'add' and not ja_favoritada):
            if ja_favoritada:
                # Remover dos favoritos
                cursor.execute(
                    '''
                    DELETE FROM candidato_vaga_favorita 
                    WHERE candidato_id = ? AND vaga_id = ?
                ''', (candidato_id, vaga_id))
                conn.commit()
                return jsonify({
                    'success': True,
                    'favorited': False,
                    'message': 'Vaga removida dos favoritos'
                })
            else:
                # Adicionar aos favoritos
                cursor.execute(
                    '''
                    INSERT INTO candidato_vaga_favorita (candidato_id, vaga_id) 
                    VALUES (?, ?)
                ''', (candidato_id, vaga_id))
                conn.commit()
                return jsonify({
                    'success': True,
                    'favorited': True,
                    'message': 'Vaga adicionada aos favoritos'
                })

        elif acao == 'remove' and ja_favoritada:
            cursor.execute(
                '''
                DELETE FROM candidato_vaga_favorita 
                WHERE candidato_id = ? AND vaga_id = ?
            ''', (candidato_id, vaga_id))
            conn.commit()
            return jsonify({
                'success': True,
                'favorited': False,
                'message': 'Vaga removida dos favoritos'
            })

        return jsonify({
            'success': True,
            'favorited': ja_favoritada,
            'message': 'Nenhuma alteração necessária'
        })

    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': f'Erro: {str(e)}'}), 500
    finally:
        conn.close()


@app.route('/api/vagas-empresa')
def api_vagas_empresa():
    """API para buscar vagas da empresa para filtros"""
    if 'empresa_id' not in session:
        return jsonify({'error': 'Não autorizado'}), 401

    conn = sqlite3.connect('recrutamento.db')
    cursor = conn.cursor()

    try:
        cursor.execute(
            'SELECT id, titulo, status FROM vagas WHERE empresa_id = ? ORDER BY titulo',
            (session['empresa_id'], ))

        vagas = []
        for row in cursor.fetchall():
            vagas.append({'id': row[0], 'titulo': row[1], 'status': row[2]})

        return jsonify(vagas)

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()


@app.route('/api/favoritar-candidato', methods=['POST'])
def favoritar_candidato():
    """API para empresa favoritar/desfavoritar candidato"""
    if 'empresa_id' not in session:
        return jsonify({'success': False, 'message': 'Não autorizado'}), 401

    data = request.get_json()
    candidato_id = data.get('candidato_id')
    vaga_id = data.get('vaga_id')
    acao = data.get('acao', 'toggle')

    if not candidato_id or not vaga_id:
        return jsonify({
            'success': False,
            'message': 'Candidato ID e Vaga ID obrigatórios'
        }), 400

    conn = sqlite3.connect('recrutamento.db')
    cursor = conn.cursor()

    try:
        empresa_id = session['empresa_id']

        # Verificar se a empresa tem acesso ao candidato (através de candidatura)
        cursor.execute(
            '''
            SELECT c.vaga_id FROM candidaturas c
            JOIN vagas v ON c.vaga_id = v.id
            WHERE c.candidato_id = ? AND v.empresa_id = ? AND c.vaga_id = ?
        ''', (candidato_id, empresa_id, vaga_id))

        if not cursor.fetchone():
            return jsonify({
                'success': False,
                'message': 'Candidato não encontrado nesta vaga'
            }), 404

        # Verificar se já está favoritado
        cursor.execute(
            '''
            SELECT id FROM empresa_candidato_favorito 
            WHERE empresa_id = ? AND candidato_id = ? AND vaga_id = ?
        ''', (empresa_id, candidato_id, vaga_id))

        ja_favoritado = cursor.fetchone() is not None

        if acao == 'toggle' or (acao == 'add' and not ja_favoritado):
            if ja_favoritado:
                # Remover dos favoritos
                cursor.execute(
                    '''
                    DELETE FROM empresa_candidato_favorito 
                    WHERE empresa_id = ? AND candidato_id = ? AND vaga_id = ?
                ''', (empresa_id, candidato_id, vaga_id))
                conn.commit()
                return jsonify({
                    'success': True,
                    'favorited': False,
                    'message': 'Candidato removido dos favoritos'
                })
            else:
                # Adicionar aos favoritos
                cursor.execute(
                    '''
                    INSERT INTO empresa_candidato_favorito (empresa_id, candidato_id, vaga_id) 
                    VALUES (?, ?, ?)
                ''', (empresa_id, candidato_id, vaga_id))
                conn.commit()
                return jsonify({
                    'success': True,
                    'favorited': True,
                    'message': 'Candidato adicionado aos favoritos'
                })

        elif acao == 'remove' and ja_favoritado:
            cursor.execute(
                '''
                DELETE FROM empresa_candidato_favorito 
                WHERE empresa_id = ? AND candidato_id = ? AND vaga_id = ?
            ''', (empresa_id, candidato_id, vaga_id))
            conn.commit()
            return jsonify({
                'success': True,
                'favorited': False,
                'message': 'Candidato removido dos favoritos'
            })

        return jsonify({
            'success': True,
            'favorited': ja_favoritado,
            'message': 'Nenhuma alteração necessária'
        })

    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': f'Erro: {str(e)}'}), 500
    finally:
        conn.close()


@app.route('/api/candidatos-favoritos')
def api_candidatos_favoritos():
    """API para listar candidatos favoritos da empresa"""
    if 'empresa_id' not in session:
        return jsonify({'error': 'Não autorizado'}), 401

    conn = sqlite3.connect('recrutamento.db')
    cursor = conn.cursor()

    try:
        cursor.execute(
            '''
            SELECT DISTINCT c.id, c.nome, c.email, c.telefone, c.linkedin,
                   v.titulo as vaga_titulo, v.id as vaga_id,
                   ca.score, ca.posicao,
                   ecf.data_criacao as data_favorito
            FROM empresa_candidato_favorito ecf
            JOIN candidatos c ON ecf.candidato_id = c.id
            JOIN vagas v ON ecf.vaga_id = v.id
            JOIN candidaturas ca ON ca.candidato_id = c.id AND ca.vaga_id = v.id
            WHERE ecf.empresa_id = ?
            ORDER BY ecf.data_criacao DESC
        ''', (session['empresa_id'], ))

        favoritos = []
        for row in cursor.fetchall():
            favoritos.append({
                'id': row[0],
                'nome': row[1],
                'email': row[2],
                'telefone': row[3],
                'linkedin': row[4],
                'vaga_titulo': row[5],
                'vaga_id': row[6],
                'score': round(row[7], 1) if row[7] else 0,
                'posicao': row[8],
                'data_favorito': row[9]
            })

        return jsonify(favoritos)

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()


@app.route('/empresa/candidatos-favoritos')
def candidatos_favoritos():
    """Página para visualizar candidatos favoritos"""
    if 'empresa_id' not in session:
        return redirect(url_for('login_empresa'))

    return render_template('candidatos_favoritos.html')


@app.route('/api/notificacoes/nao-lidas')
def api_notificacoes_nao_lidas():
    """API para contar notificações não lidas"""
    if 'candidato_id' not in session:
        return jsonify({'count': 0})

    candidato_id = session['candidato_id']
    count = contar_notificacoes_nao_lidas(candidato_id)

    return jsonify({'count': count})


@app.route('/api/notificacoes/<int:notificacao_id>/marcar-lida',
           methods=['POST'])
def api_marcar_notificacao_lida(notificacao_id):
    """API para marcar notificação individual como lida"""
    if 'candidato_id' not in session:
        return jsonify({'success': False, 'message': 'Acesso negado'})

    candidato_id = session['candidato_id']
    sucesso = marcar_notificacao_como_lida(notificacao_id, candidato_id)

    return jsonify({'success': sucesso})


@app.route('/api/notificacoes/marcar-todas-lidas', methods=['POST'])
def api_marcar_todas_lidas():
    """API para marcar todas as notificações como lidas"""
    if 'candidato_id' not in session:
        return jsonify({'success': False, 'message': 'Acesso negado'})

    candidato_id = session['candidato_id']
    count = marcar_todas_notificacoes_como_lidas(candidato_id)

    return jsonify({'success': True, 'count': count})


@app.route('/api/todas-vagas')
def api_todas_vagas():
    """API para buscar todas as vagas disponíveis para o candidato"""
    if 'candidato_id' not in session:
        return jsonify({'error': 'Não autorizado'}), 401

    conn = sqlite3.connect('recrutamento.db')
    cursor = conn.cursor()

    try:
        # Buscar todas as vagas ativas
        cursor.execute(
            '''
            SELECT v.id, v.titulo, v.descricao, v.requisitos, v.salario_oferecido, 
                   e.nome as empresa_nome, v.diferenciais, v.tipo_vaga, v.endereco_vaga,
                   CASE WHEN cvf.id IS NOT NULL THEN 1 ELSE 0 END as is_favorita,
                   CASE WHEN ca.id IS NOT NULL THEN 1 ELSE 0 END as ja_candidatou
            FROM vagas v
            JOIN empresas e ON v.empresa_id = e.id
            LEFT JOIN candidato_vaga_favorita cvf ON cvf.candidato_id = ? AND cvf.vaga_id = v.id
            LEFT JOIN candidaturas ca ON ca.candidato_id = ? AND ca.vaga_id = v.id
            WHERE v.status = 'Ativa'
            ORDER BY v.data_criacao DESC
        ''', (session['candidato_id'], session['candidato_id']))

        vagas_raw = cursor.fetchall()

        # Buscar informações do candidato para calcular scores
        cursor.execute(
            'SELECT pretensao_salarial, texto_curriculo, endereco_completo FROM candidatos WHERE id = ?',
            (session['candidato_id'], ))
        candidato_info = cursor.fetchone()

        conn.close()

        if not candidato_info:
            return jsonify({'error': 'Candidato não encontrado'}), 404

        # Calcular scores
        avaliador = criar_avaliador(MODO_IA)
        vagas_processadas = []

        for vaga in vagas_raw:
            score = avaliador.calcular_score(
                candidato_info[1], vaga[3], candidato_info[0], vaga[4],
                vaga[6] if vaga[6] else '',
                candidato_info[2] if len(candidato_info) > 2 else None,
                vaga[8], vaga[7])

            vaga_processada = {
                'id': int(vaga[0]),
                'titulo': vaga[1],
                'descricao': vaga[2],
                'requisitos': vaga[3],
                'salario_oferecido': float(vaga[4]) if vaga[4] else 0.0,
                'empresa_nome': vaga[5],
                'diferenciais': vaga[6] or '',
                'tipo_vaga': vaga[7] or 'Presencial',
                'endereco_vaga': vaga[8] or '',
                'is_favorita': bool(vaga[9]),
                'ja_candidatou': bool(vaga[10]),
                'score': float(score)
            }
            vagas_processadas.append(vaga_processada)

        # Ordenar por score
        vagas_processadas.sort(key=lambda x: x['score'], reverse=True)

        return jsonify(vagas_processadas)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/busca-filtros')
def api_busca_filtros():
    """API para obter filtros disponíveis para busca"""
    if 'candidato_id' not in session:
        return jsonify({'error': 'Não autorizado'}), 401

    conn = sqlite3.connect('recrutamento.db')
    cursor = conn.cursor()

    try:
        # Buscar categorias
        cursor.execute('SELECT id, nome FROM categorias ORDER BY nome')
        categorias = [{
            'id': row[0],
            'nome': row[1]
        } for row in cursor.fetchall()]

        # Buscar localizações únicas das vagas ativas
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

        # Remover duplicatas e manter ordenação
        localizacoes = list(dict.fromkeys(localizacoes))

        return jsonify({
            'categorias': categorias,
            'localizacoes': localizacoes
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()


@app.route('/api/buscar-vagas')
def api_buscar_vagas():
    """API para busca avançada de vagas com filtros"""
    if 'candidato_id' not in session:
        return jsonify({'error': 'Não autorizado'}), 401

    # Obter parâmetros de busca
    keyword = request.args.get('keyword', '').strip()
    location = request.args.get('location', '').strip()
    category = request.args.get('category', '').strip()
    urgency = request.args.get('urgency', '').strip()
    salary = request.args.get('salary', '').strip()
    job_type = request.args.get('type', '').strip()

    conn = sqlite3.connect('recrutamento.db')
    cursor = conn.cursor()

    try:
        # Construir query base
        query_base = '''
            SELECT v.id, v.titulo, v.descricao, v.requisitos, v.salario_oferecido, 
                   e.nome as empresa_nome, v.diferenciais, v.tipo_vaga, v.endereco_vaga,
                   CASE WHEN cvf.id IS NOT NULL THEN 1 ELSE 0 END as is_favorita,
                   CASE WHEN ca.id IS NOT NULL THEN 1 ELSE 0 END as ja_candidatou,
                   v.urgencia_contratacao, v.localizacao_cidade, v.localizacao_estado,
                   c.nome as categoria_nome
            FROM vagas v
            JOIN empresas e ON v.empresa_id = e.id
            LEFT JOIN candidato_vaga_favorita cvf ON cvf.candidato_id = ? AND cvf.vaga_id = v.id
            LEFT JOIN candidaturas ca ON ca.candidato_id = ? AND ca.vaga_id = v.id
            LEFT JOIN categorias c ON v.categoria_id = c.id
            WHERE v.status = 'Ativa'
        '''

        params = [session['candidato_id'], session['candidato_id']]

        # Adicionar filtros
        if keyword:
            query_base += ' AND (v.titulo LIKE ? OR v.descricao LIKE ? OR v.requisitos LIKE ?)'
            keyword_param = f'%{keyword}%'
            params.extend([keyword_param, keyword_param, keyword_param])

        if location:
            query_base += ' AND (v.localizacao_cidade LIKE ? OR v.localizacao_estado LIKE ?)'
            location_param = f'%{location}%'
            params.extend([location_param, location_param])

        if category:
            query_base += ' AND v.categoria_id = ?'
            params.append(category)

        if urgency:
            query_base += ' AND v.urgencia_contratacao = ?'
            params.append(urgency)

        if salary:
            try:
                salary_value = float(salary)
                query_base += ' AND v.salario_oferecido >= ?'
                params.append(salary_value)
            except ValueError:
                pass

        if job_type:
            query_base += ' AND v.tipo_vaga = ?'
            params.append(job_type)

        query_base += ' ORDER BY v.data_criacao DESC'

        cursor.execute(query_base, params)
        vagas_raw = cursor.fetchall()

        # Buscar informações do candidato para calcular scores
        cursor.execute(
            'SELECT pretensao_salarial, texto_curriculo, endereco_completo FROM candidatos WHERE id = ?',
            (session['candidato_id'], ))
        candidato_info = cursor.fetchone()

        if not candidato_info:
            return jsonify({'error': 'Candidato não encontrado'}), 404

        # Calcular scores
        avaliador = criar_avaliador(MODO_IA)
        vagas_processadas = []

        for vaga in vagas_raw:
            score = avaliador.calcular_score(
                candidato_info[1], vaga[3], candidato_info[0], vaga[4],
                vaga[6] if vaga[6] else '',
                candidato_info[2] if len(candidato_info) > 2 else None,
                vaga[8], vaga[7])

            vaga_processada = {
                'id':
                int(vaga[0]),
                'titulo':
                vaga[1],
                'descricao':
                vaga[2],
                'requisitos':
                vaga[3],
                'salario_oferecido':
                float(vaga[4]) if vaga[4] else 0.0,
                'empresa_nome':
                vaga[5],
                'diferenciais':
                vaga[6] or '',
                'tipo_vaga':
                vaga[7] or 'Presencial',
                'endereco_vaga':
                vaga[8] or '',
                'is_favorita':
                bool(vaga[9]),
                'ja_candidatou':
                bool(vaga[10]),
                'urgencia':
                vaga[11],
                'localizacao':
                f"{vaga[12]}, {vaga[13]}"
                if vaga[12] and vaga[13] else vaga[12] or '',
                'categoria':
                vaga[14],
                'score':
                float(score)
            }
            vagas_processadas.append(vaga_processada)

        # Ordenar por score
        vagas_processadas.sort(key=lambda x: x['score'], reverse=True)

        return jsonify(vagas_processadas)

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()


# This is the final code file with the requested changes.
if __name__ == '__main__':
    inicializar_banco()

    # Iniciar scheduler em background
    try:
        iniciar_scheduler_background()
        print("Sistema de agendamento iniciado com sucesso!")
    except Exception as e:
        print(f"Erro ao iniciar scheduler: {e}")

    app.run(host='0.0.0.0', port=5001, debug=True)

# =========================
# ROTAS DO ASSISTENTE IA
# =========================


@app.route('/api/ia/analisar-curriculo')
def api_analisar_curriculo():
    """API para análise IA do currículo do candidato"""
    if 'candidato_id' not in session:
        return jsonify({'error': 'Não autorizado'}), 401

    conn = sqlite3.connect('recrutamento.db')
    cursor = conn.cursor()

    try:
        candidato_id = session['candidato_id']

        # Buscar currículo do candidato
        cursor.execute('SELECT texto_curriculo FROM candidatos WHERE id = ?',
                       (candidato_id, ))
        resultado = cursor.fetchone()

        if not resultado or not resultado[0]:
            return jsonify({'error': 'Currículo não encontrado'}), 404

        curriculo_texto = resultado[0]

        # Analisar currículo com IA
        analise = ia_assistant.analisar_curriculo(candidato_id,
                                                  curriculo_texto)

        return jsonify(analise)

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()


@app.route('/api/ia/recomendacoes-vagas')
def api_recomendacoes_ia():
    """API para recomendações personalizadas de vagas"""
    if 'candidato_id' not in session:
        return jsonify({'error': 'Não autorizado'}), 401

    conn = sqlite3.connect('recrutamento.db')
    cursor = conn.cursor()

    try:
        candidato_id = session['candidato_id']

        # Buscar currículo do candidato
        cursor.execute('SELECT texto_curriculo FROM candidatos WHERE id = ?',
                       (candidato_id, ))
        resultado = cursor.fetchone()

        if not resultado or not resultado[0]:
            return jsonify({'error': 'Currículo não encontrado'}), 404

        curriculo_texto = resultado[0]

        # Obter recomendações da IA
        recomendacoes = ia_assistant.recomendar_vagas_personalizadas(
            candidato_id, curriculo_texto)

        return jsonify(recomendacoes)

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()


@app.route('/api/ia/dicas-vaga/<int:vaga_id>')
def api_dicas_vaga_ia(vaga_id):
    """API para dicas específicas de uma vaga"""
    if 'candidato_id' not in session:
        return jsonify({'error': 'Não autorizado'}), 401

    conn = sqlite3.connect('recrutamento.db')
    cursor = conn.cursor()

    try:
        candidato_id = session['candidato_id']

        # Buscar dados do candidato e da vaga
        cursor.execute(
            '''
            SELECT c.texto_curriculo, v.requisitos, v.salario_oferecido
            FROM candidatos c, vagas v
            WHERE c.id = ? AND v.id = ? AND v.status = 'Ativa'
        ''', (candidato_id, vaga_id))

        resultado = cursor.fetchone()

        if not resultado:
            return jsonify({'error': 'Dados não encontrados'}), 404

        curriculo_texto, requisitos_vaga, salario_vaga = resultado

        # Gerar dicas da IA
        dicas = ia_assistant.gerar_dicas_melhoria_vaga(curriculo_texto,
                                                       requisitos_vaga,
                                                       salario_vaga)

        return jsonify(dicas)

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()


@app.route('/api/ia/enviar-recomendacoes', methods=['POST'])
def api_enviar_recomendacoes_email():
    """API para enviar recomendações por email"""
    if 'candidato_id' not in session:
        return jsonify({'error': 'Não autorizado'}), 401

    conn = sqlite3.connect('recrutamento.db')
    cursor = conn.cursor()

    try:
        candidato_id = session['candidato_id']

        # Buscar dados do candidato
        cursor.execute(
            'SELECT nome, email, texto_curriculo FROM candidatos WHERE id = ?',
            (candidato_id, ))
        resultado = cursor.fetchone()

        if not resultado:
            return jsonify({'error': 'Candidato não encontrado'}), 404

        candidato_nome, candidato_email, curriculo_texto = resultado

        # Obter análise e recomendações
        analise = ia_assistant.analisar_curriculo(candidato_id,
                                                  curriculo_texto)
        recomendacoes = ia_assistant.recomendar_vagas_personalizadas(
            candidato_id, curriculo_texto)

        # Gerar dicas gerais
        dicas = []
        if analise['areas_melhoria']:
            for area in analise['areas_melhoria'][:3]:
                dicas.append({
                    'titulo': f"Melhore: {area}",
                    'descricao':
                    f"Considere desenvolver mais esta área do seu perfil",
                    'prioridade': 'media',
                    'icone': '💡'
                })

        # Dados para o template
        template_data = {
            'candidato_nome': candidato_nome,
            'analise': analise,
            'recomendacoes': recomendacoes,
            'dicas': dicas
        }

        # Enviar email com template da IA
        assunto = "🤖 Recomendações Personalizadas da IA"
        sucesso = notification_system.enviar_email(
            candidato_email, assunto,
            "Suas recomendações personalizadas estão prontas!", template_data,
            'recomendacao_ia')

        if sucesso:
            return jsonify({
                'success': True,
                'message': 'Recomendações enviadas por email!'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Erro ao enviar email'
            }), 500

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()
