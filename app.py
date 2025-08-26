import os
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_file
from utils.helpers import inicializar_banco, calcular_distancia_endereco
from utils.resume_extractor import processar_upload_curriculo, finalizar_processamento_curriculo
from avaliador import criar_avaliador
import mysql.connector
from PyPDF2 import PdfReader
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import io
import json
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
from functools import lru_cache
import threading
from collections import Counter
from datetime import datetime

data_brasil = (datetime.utcnow() -
               timedelta(hours=3)).strftime('%Y-%m-%d %H:%M:%S')

load_dotenv()

app = Flask(__name__)

# Cache para conexões de banco
_db_connections = threading.local()



def get_db_connection():
    """Obtém conexão de banco no MySQL (XAMPP)"""
    conn = mysql.connector.connect(
        host="localhost",
        user="root",         # ajuste conforme sua config
        password="",         # senha (em branco no XAMPP por padrão)
        database="recrutamentodb",
        connection_timeout=60  # timeout de 60s
    )
    return conn

# Cache de configuração
@lru_cache(maxsize=1)
def get_config():
    return {
        'MODO_IA': os.getenv('MODO_IA', 'local'),
        'TOP_JOBS': int(os.getenv('TOP_JOBS', '3'))
    }

# Inicializar assistente IA (lazy loading)
_ia_assistant = None

def get_ia_assistant():
    global _ia_assistant
    if _ia_assistant is None:
        _ia_assistant = IAAssistant()
    return _ia_assistant

app.secret_key = 'chave-secreta-mvp-recrutamento-2024'
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_TYPE'] = 'filesystem'

# Cache para avaliadores
_avaliadores_cache = {}

def get_avaliador(modo='local'):
    """Cache de avaliadores para evitar recriar objetos"""
    if modo not in _avaliadores_cache:
        _avaliadores_cache[modo] = criar_avaliador(modo)
    return _avaliadores_cache[modo]

@lru_cache(maxsize=100)
def gerar_feedback_ia_vaga_cached(total, alta_compatibilidade, media_compatibilidade, baixa_compatibilidade):
    """Versão cached do feedback IA"""
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


@app.route('/vaga-publico/<int:vaga_id>')
def detalhes_vaga_publico(vaga_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        '''
        SELECT v.*, e.nome as empresa_nome
        FROM vagas v
        JOIN empresas e ON v.empresa_id = e.id
        WHERE v.id = %s AND v.status = 'Ativa'
    ''', (vaga_id, ))
    vaga_data = cursor.fetchone()

    if not vaga_data:
        flash('Vaga não encontrada ou não está mais ativa', 'error')
        return redirect(url_for('index'))

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

    return render_template('detalhes_vaga_publico.html',
                           vaga=vaga,
                           empresa=empresa)



@app.route('/empresa/login_empresa', methods=['GET', 'POST'])
def login_empresa():
    if request.method == 'POST':
        cnpj = request.form.get('cnpj', '').strip()
        senha = request.form.get('senha', '')

        if not cnpj or not senha:
            flash('Por favor, preencha todos os campos', 'error')
            return render_template('empresa/login_empresa.html')

        conn = get_db_connection()
        cursor = conn.cursor(buffered=True)  # <-- Adicionado buffered=True

        try:
            cursor.execute(
                'SELECT id, senha_hash FROM empresas WHERE cnpj = %s',
                (cnpj,)
            )
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
            cursor.close()
            conn.close()

    return render_template('empresa/login_empresa.html')


@app.route('/empresa/cadastro_empresa', methods=['GET', 'POST'])
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

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                '''
                INSERT INTO empresas (nome, email, senha_hash, cnpj, endereco, cidade, estado, cep)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ''',
                (nome, email, generate_password_hash(senha), cnpj, endereco,
                 cidade, estado, cep)
            )
            conn.commit()
            flash('Empresa cadastrada com sucesso!', 'success')
            return redirect(url_for('login_empresa'))
        except mysql.connector.IntegrityError:
            flash('Email ou CNPJ já cadastrados', 'error')
        finally:
            cursor.close()
            conn.close()

    return render_template('empresa/cadastro_empresa.html')


@app.route('/candidato/login_candidato', methods=['GET', 'POST'])
@app.route('/index.html', methods=['GET', 'POST'])
def login_candidato():
    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['senha']

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT id, senha_hash FROM candidatos WHERE email = %s',
                       (email, ))
        candidato = cursor.fetchone()

        if candidato and check_password_hash(candidato[1], senha):
            session['candidato_id'] = candidato[0]
            session['tipo_usuario'] = 'candidato'
            return redirect(url_for('dashboard_candidato'))
        else:
            flash('Email ou senha incorretos', 'error')

    return render_template('candidato/login_candidato.html')




@app.route('/candidato/cadastro_candidato', methods=['GET', 'POST'])
def cadastro_candidato():
    if request.method == 'POST':
        nome = request.form['nome']
        email = request.form['email']
        senha = request.form['senha']
        telefone = request.form['telefone']
        linkedin = request.form['linkedin']
        pretensao_salarial = float(request.form['pretensao_salarial'])

        # Novo formato de endereço
        cep = request.form['cep']
        endereco = request.form['endereco']  # logradouro + bairro + cidade - estado
        numero = request.form['numero']
        complemento = request.form.get('complemento', '')

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                '''INSERT INTO candidatos 
                   (nome, email, senha_hash, telefone, linkedin, cep, endereco, numero, complemento, pretensao_salarial)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)''',
                (nome, email, generate_password_hash(senha), telefone, linkedin,
                 cep, endereco, numero, complemento, pretensao_salarial)
            )
            conn.commit()
            flash('Candidato cadastrado com sucesso!', 'success')
            return redirect(url_for('login_candidato'))
        except mysql.connector.IntegrityError:
            flash('Email já cadastrado', 'error')
        finally:
            conn.close()

    return render_template('candidato/cadastro_candidato.html')


@app.route('/empresa/dashboard_empresa')
def dashboard_empresa():
    if 'empresa_id' not in session or session.get('tipo_usuario') != 'empresa':
        flash('Faça login para acessar esta página', 'error')
        return redirect(url_for('login_empresa'))

    conn = get_db_connection()
    cursor = conn.cursor()

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

    return render_template('empresa/dashboard_empresa.html', vagas=vagas_processadas)


@app.route('/empresa/criar_vaga', methods=['GET', 'POST'])
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

    return render_template('empresa/criar_vaga.html', categorias=categorias, hoje=hoje)





@app.route('/candidato/candidatos_vaga/<int:vaga_id>')
def candidatos_vaga(vaga_id):
    if 'empresa_id' not in session:
        return redirect(url_for('login_empresa'))

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        '''SELECT c.nome, c.email, c.telefone, c.linkedin, ca.score, ca.posicao, c.id, c.endereco_completo
           FROM candidaturas ca
           JOIN candidatos c ON ca.candidato_id = c.id
           WHERE ca.vaga_id = %s
           ORDER BY ca.score DESC''', (vaga_id, ))

    candidatos = cursor.fetchall()

    cursor.execute('SELECT titulo FROM vagas WHERE id = %s', (vaga_id, ))
    vaga = cursor.fetchone()
    conn.close()

    return render_template('candidato/candidatos_vaga.html',
                           candidatos=candidatos,
                           vaga_titulo=vaga[0] if vaga else '',
                           vaga_id=vaga_id)


@app.route('/candidato/dashboard_candidato')
def dashboard_candidato():
    if 'candidato_id' not in session:
        return redirect(url_for('login_candidato'))

    conn = get_db_connection()
    cursor = conn.cursor()

    # Verifica se o candidato já enviou currículo
    cursor.execute('SELECT resumo_profissional FROM candidatos WHERE id = %s',
                   (session['candidato_id'],))
    candidato = cursor.fetchone()

    if not candidato or not candidato[0]:
        conn.close()
        return redirect(url_for('upload_curriculo'))

    # Candidaturas em vagas ATIVAS
    cursor.execute(
        '''
        SELECT v.id, v.titulo, e.nome AS empresa_nome, v.salario_oferecido, ca.score, ca.posicao,
               CASE WHEN cvf.id IS NOT NULL THEN 1 ELSE 0 END as is_favorita
        FROM candidaturas ca
        JOIN vagas v ON ca.vaga_id = v.id
        JOIN empresas e ON v.empresa_id = e.id
        LEFT JOIN candidato_vaga_favorita cvf ON cvf.candidato_id = %s AND cvf.vaga_id = v.id
        WHERE ca.candidato_id = %s AND v.status = 'Ativa'
        ORDER BY ca.score DESC
        ''', (session['candidato_id'], session['candidato_id']))
    vagas_candidatadas_raw = cursor.fetchall()

    vagas_candidatadas = []
    for vaga in vagas_candidatadas_raw:
        vaga_processada = (
            int(vaga[0]),
            vaga[1],
            vaga[2],
            float(vaga[3]) if vaga[3] else 0.0,
            float(vaga[4]) if vaga[4] else 0.0,
            int(vaga[5]) if vaga[5] else 0,
            bool(vaga[6])
        )
        vagas_candidatadas.append(vaga_processada)

    # Vagas disponíveis
    cursor.execute(
        '''
        SELECT v.id, v.titulo, v.descricao, v.requisitos, v.salario_oferecido,
               e.nome as empresa_nome, v.diferenciais, v.tipo_vaga, v.endereco_vaga,
               CASE WHEN cvf.id IS NOT NULL THEN 1 ELSE 0 END as is_favorita
        FROM vagas v
        JOIN empresas e ON v.empresa_id = e.id
        LEFT JOIN candidato_vaga_favorita cvf ON cvf.candidato_id = %s AND cvf.vaga_id = v.id
        WHERE v.id NOT IN (
            SELECT vaga_id FROM candidaturas WHERE candidato_id = %s
        ) AND v.status = 'Ativa'
        ''', (session['candidato_id'], session['candidato_id']))
    vagas_disponiveis = cursor.fetchall()

    # Vagas favoritas
    cursor.execute(
        '''
        SELECT v.id, v.titulo, v.descricao, v.requisitos, v.salario_oferecido,
               e.nome as empresa_nome, v.diferenciais, v.tipo_vaga, v.endereco_vaga,
               CASE WHEN ca.id IS NOT NULL THEN 1 ELSE 0 END as ja_candidatou,
               ca.score, ca.posicao
        FROM candidato_vaga_favorita cvf
        JOIN vagas v ON cvf.vaga_id = v.id
        JOIN empresas e ON v.empresa_id = e.id
        LEFT JOIN candidaturas ca ON ca.candidato_id = %s AND ca.vaga_id = v.id
        WHERE cvf.candidato_id = %s AND v.status = 'Ativa'
        ORDER BY cvf.data_criacao DESC
        ''', (session['candidato_id'], session['candidato_id']))
    vagas_favoritas = cursor.fetchall()

    # Informações do candidato com endereço simplificado
    cursor.execute(
        '''
        SELECT pretensao_salarial, resumo_profissional, endereco, cep 
        FROM candidatos WHERE id = %s
        ''', (session['candidato_id'],))
    candidato_info = cursor.fetchone()
    conn.close()

    config = get_config()
    avaliador = get_avaliador(config['MODO_IA'])
    vagas_com_score = []

    for vaga in vagas_disponiveis:
        score = avaliador.calcular_score(
            candidato_info[1], vaga[3], candidato_info[0], vaga[4],
            vaga[6] if vaga[6] else '',
            candidato_info[2] if len(candidato_info) > 2 else None,
            vaga[8], vaga[7]
        )
        vaga_processada = (
            int(vaga[0]), vaga[1], vaga[2], vaga[3],
            float(vaga[4]) if vaga[4] else 0.0, vaga[5],
            vaga[6] or '', vaga[7] or 'Presencial', vaga[8] or '',
            float(score), bool(vaga[9])
        )
        vagas_com_score.append(vaga_processada)

    vagas_favoritas_processadas = []
    for vaga in vagas_favoritas:
        if not vaga[9]:
            score = avaliador.calcular_score(
                candidato_info[1], vaga[3], candidato_info[0], vaga[4],
                vaga[6] if vaga[6] else '',
                candidato_info[2] if len(candidato_info) > 2 else None,
                vaga[8], vaga[7]
            )
        else:
            score = vaga[10]

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

    vagas_com_score.sort(key=lambda x: x[9], reverse=True)
    top_vagas = vagas_com_score[:config['TOP_JOBS']]

    return render_template('candidato/dashboard_candidato.html',
                           vagas_recomendadas=top_vagas,
                           vagas_candidatadas=vagas_candidatadas,
                           vagas_favoritas=vagas_favoritas_processadas)



@app.route('/candidato/upload_curriculo', methods=['GET', 'POST'])
def upload_curriculo():
    if 'candidato_id' not in session:
        return redirect(url_for('login_candidato'))

    if request.method == 'POST':
        resultado = processar_upload_curriculo(request, session['candidato_id'])

        for mensagem in resultado['mensagens']:
            if isinstance(mensagem, dict) and 'texto' in mensagem:
                flash(mensagem['texto'], mensagem.get('tipo', 'info'))
            else:
                flash(str(mensagem), 'info')

        if resultado['sucesso']:
            # Passa dados extraídos para o template de revisão
            return render_template(
                'candidato/processar_curriculo.html',
                dados_extraidos=resultado['dados_extraidos']
            )
        else:
            # Erro no upload/processamento, permanece na página
            return redirect(request.url)

    return render_template('candidato/upload_curriculo.html')


@app.route('/finalizar_curriculo', methods=['POST'])
def finalizar_curriculo():
    if 'candidato_id' not in session:
        return redirect(url_for('login_candidato'))

    candidato_id = session['candidato_id']
    resultado = finalizar_processamento_curriculo(request, candidato_id)

    for mensagem in resultado['mensagens']:
        if isinstance(mensagem, dict) and 'texto' in mensagem:
            flash(mensagem['texto'], mensagem.get('tipo', 'info'))
        else:
            flash(str(mensagem), 'info')

    if resultado['sucesso']:
        return redirect(url_for('dashboard_candidato'))
    else:
        # Reexibe formulário com os dados preenchidos em caso de erro
        dados_extraidos = {
            'experiencia': request.form.get('experiencia', ''),
            'competencias': request.form.get('competencias', ''),
            'resumo_profissional': request.form.get('resumo_profissional', ''),
            'formacao': request.form.get('formacao', '')
        }
        return render_template('candidato/processar_curriculo.html', dados_extraidos=dados_extraidos)

@app.route('/candidatar/<int:vaga_id>')
def candidatar(vaga_id):
    if 'candidato_id' not in session:
        return redirect(url_for('login_candidato'))

    from utils.helpers import processar_candidatura
    config = get_config()
    resultado = processar_candidatura(session['candidato_id'], vaga_id,
                                      config['MODO_IA'])

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

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        '''SELECT c.id, c.nome, ca.score
           FROM candidaturas ca
           JOIN candidatos c ON ca.candidato_id = c.id
           JOIN vagas v ON ca.vaga_id = v.id
           WHERE ca.vaga_id = %s AND v.empresa_id = %s
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

    # Usar nova conexão com timeout maior e WAL mode
    conn = mysql.connect('recrutamentodb', timeout=60.0)
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA busy_timeout=60000')
    conn.execute('PRAGMA synchronous=NORMAL')
    cursor = conn.cursor()

    try:
        # Verificar se a vaga pertence à empresa
        cursor.execute('SELECT titulo FROM vagas WHERE id = %s AND empresa_id = %s',
                       (vaga_id, session['empresa_id']))
        vaga_info = cursor.fetchone()
        if not vaga_info:
            return jsonify({'error': 'Vaga não encontrada'}), 404

        vaga_titulo = vaga_info[0]

        # Buscar candidatos da vaga
        cursor.execute('SELECT candidato_id FROM candidaturas WHERE vaga_id = %s',
                       (vaga_id, ))
        todos_candidatos = [row[0] for row in cursor.fetchall()]

        if acao == 'contratar':
            if not candidato_id:
                return jsonify({'error': 'Candidato não selecionado'}), 400

            # Verificar se o candidato se candidatou
            cursor.execute(
                'SELECT id FROM candidaturas WHERE candidato_id = %s AND vaga_id = %s',
                (candidato_id, vaga_id))
            if not cursor.fetchone():
                return jsonify(
                    {'error': 'Candidato não se candidatou a esta vaga'}), 400

            # Verificar se o candidato existe
            cursor.execute('SELECT nome FROM candidatos WHERE id = %s',
                           (candidato_id, ))
            candidato_info = cursor.fetchone()

            if not candidato_info:
                return jsonify({'error': 'Candidato não encontrado'}), 404

            # Atualizar vaga como concluída
            cursor.execute(
                '''UPDATE vagas
                   SET status = "Concluída", candidato_selecionado_id = %s
                   WHERE id = %s''', (candidato_id, vaga_id))

            conn.commit()  # Commit imediato

            # Notificar candidato contratado em nova conexão
            print(f"📋 Lista de todos os candidatos: {todos_candidatos}")
            print(f"🎯 Candidato selecionado: {candidato_id}")

            try:
                sucesso_contratacao = notification_system.notificar_contratacao(
                    candidato_id, vaga_id, session['empresa_id'], mensagem_personalizada)
                print(f"✅ Notificação de contratação enviada: {sucesso_contratacao}")
            except Exception as e:
                print(f"❌ Erro ao notificar contratação: {e}")

            # Notificar outros candidatos
            outros_candidatos = [cid for cid in todos_candidatos if cid != candidato_id]
            print(f"📢 Notificando outros {len(outros_candidatos)} candidatos")

            for cid in outros_candidatos:
                print(f"🔔 Processando notificação para candidato {cid}")
                try:
                    msg = f"A vaga '{vaga_titulo}' foi concluída. Outro candidato foi selecionado."
                    sucesso_notif = notification_system.criar_notificacao(
                        cid, msg, vaga_id, session['empresa_id'], 'vaga_concluida')
                    print(f"📝 Notificação criada para candidato {cid}: {sucesso_notif}")

                    # Buscar email em nova conexão
                    conn_email = mysql.connect('recrutamentodb', timeout=30.0)
                    cursor_email = conn_email.cursor()
                    cursor_email.execute('SELECT email FROM candidatos WHERE id = %s', (cid, ))
                    email_result = cursor_email.fetchone()
                    conn_email.close()

                    if email_result:
                        notification_system.enviar_email(
                            email_result[0], f"Vaga Concluída - {vaga_titulo}", msg)
                        print(f"📧 Email enviado para candidato {cid}")
                    else:
                        print(f"⚠️ Email não encontrado para candidato {cid}")
                except Exception as e:
                    print(f"❌ Erro ao notificar candidato {cid}: {e}")

            response = {
                'success': True,
                'message': f'Candidato {candidato_info[0]} contratado com sucesso!'
            }

        elif acao == 'congelar':
            cursor.execute('UPDATE vagas SET status = "Congelada" WHERE id = %s',
                           (vaga_id, ))
            conn.commit()  # Commit imediato

            try:
                notification_system.notificar_vaga_congelada(vaga_id)
            except Exception as e:
                print(f"Erro ao notificar congelamento: {e}")

            response = {
                'success': True,
                'message': 'Vaga congelada com sucesso!'
            }

        elif acao == 'excluir':
            # Notificar antes de excluir
            try:
                notification_system.notificar_vaga_excluida(vaga_id)
            except Exception as e:
                print(f"Erro ao notificar exclusão: {e}")

            # Excluir candidaturas e vaga
            cursor.execute('DELETE FROM candidaturas WHERE vaga_id = %s', (vaga_id, ))
            cursor.execute('DELETE FROM vagas WHERE id = %s', (vaga_id, ))
            conn.commit()

            response = {
                'success': True,
                'message': 'Vaga excluída com sucesso!'
            }

        elif acao == 'reativar':
            cursor.execute('UPDATE vagas SET status = "Ativa" WHERE id = %s',
                           (vaga_id, ))
            conn.commit()  # Commit imediato

            # Notificar candidatos sobre reativação
            for cid in todos_candidatos:
                try:
                    msg = f"Boa notícia! A vaga '{vaga_titulo}' foi reativada. Sua candidatura continua válida e o processo seletivo foi retomado."
                    notification_system.criar_notificacao(cid, msg, vaga_id,
                                                          session['empresa_id'],
                                                          'vaga_reativada')

                    # Buscar email em nova conexão
                    conn_email = mysql.connect('recrutamentodb', timeout=30.0)
                    cursor_email = conn_email.cursor()
                    cursor_email.execute('SELECT email FROM candidatos WHERE id = %s', (cid, ))
                    email_result = cursor_email.fetchone()
                    conn_email.close()

                    if email_result:
                        notification_system.enviar_email(
                            email_result[0], f"Vaga Reativada - {vaga_titulo}", msg)
                except Exception as e:
                    print(f"Erro ao notificar reativação para candidato {cid}: {e}")

            response = {
                'success': True,
                'message': 'Vaga reativada com sucesso!'
            }

        else:
            return jsonify({'error': 'Ação inválida'}), 400

        return jsonify(response)

    except mysql.OperationalError as e:
        if 'database is locked' in str(e):
            # Tentar novamente após delay
            import time
            time.sleep(1)
            try:
                conn.rollback()
                return jsonify({'error': 'Sistema ocupado, tente novamente'}), 503
            except:
                pass
        conn.rollback()
        print(f"Erro de banco ao encerrar vaga: {e}")
        return jsonify({'error': f'Erro de banco: {str(e)}'}), 500
    except Exception as e:
        conn.rollback()
        print(f"Erro ao encerrar vaga: {e}")
        return jsonify({'error': f'Erro ao processar ação: {str(e)}'}), 500
    finally:
        try:
            conn.close()
        except:
            pass


@app.route('/candidato/editar_perfil_candidato', methods=['GET', 'POST'])
def editar_perfil_candidato():
    if 'candidato_id' not in session:
        return redirect(url_for('login_candidato'))

    conn = get_db_connection()
    cursor = conn.cursor()
    candidato_id = session['candidato_id']

    if request.method == 'POST':
        nome = request.form['nome']
        telefone = request.form['telefone']
        linkedin = request.form['linkedin']
        pretensao_salarial = float(request.form['pretensao_salarial'])
        experiencia = request.form['experiencia']
        competencias = request.form['competencias']
        resumo_profissional = request.form['resumo_profissional']

        # Se você estiver lidando com upload de arquivo:
        file = request.files.get('curriculo')
        if file and file.filename:
            caminho_curriculo = file.filename
            # Salve o arquivo, se necessário
            # file.save(os.path.join('caminho_para_salvar', file.filename))

            # Exemplo fictício de extração de texto
            texto_extraido = "Texto extraído do currículo"

            cursor.execute("""
                UPDATE candidatos
                SET nome=%s,
                    telefone=%s,
                    linkedin=%s,
                    pretensao_salarial=%s,
                    experiencia=%s,
                    competencias=%s,
                    resumo_profissional=%s,
                    caminho_curriculo=%s,
                    resumo_profissional=%s
                WHERE id=%s
            """, (
                nome, telefone, linkedin, pretensao_salarial,
                experiencia, competencias, resumo_profissional,
                caminho_curriculo, texto_extraido, candidato_id
            ))
        else:
            # Atualização sem novo currículo
            cursor.execute("""
                UPDATE candidatos
                SET nome=%s,
                    telefone=%s,
                    linkedin=%s,
                    pretensao_salarial=%s,
                    experiencia=%s,
                    competencias=%s,
                    resumo_profissional=%s
                WHERE id=%s
            """, (
                nome, telefone, linkedin, pretensao_salarial,
                experiencia, competencias, resumo_profissional,
                candidato_id
            ))

        conn.commit()
        conn.close()

        flash('Perfil atualizado com sucesso!', 'success')
        return redirect(url_for('dashboard_candidato'))  # Corrigido o nome da rota

    # Método GET – carregar dados atuais
    cursor.execute("""
        SELECT nome, telefone, linkedin, pretensao_salarial,
               experiencia, competencias, resumo_profissional
        FROM candidatos WHERE id = %s
    """, (candidato_id, ))

    candidato = cursor.fetchone()
    conn.close()

    return render_template('candidato/editar_perfil_candidato.html', candidato=candidato)


@app.route('/empresa/editar_vaga/<int:vaga_id>', methods=['GET', 'POST'])
def editar_vaga(vaga_id):
    if 'empresa_id' not in session:
        flash('Acesso negado', 'error')
        return redirect(url_for('login_empresa'))

    conn = get_db_connection()
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
        data_congelamento_agendado = request.form.get('data_congelamento_agendado') or None
        usar_endereco_empresa = 'usar_endereco_empresa' in request.form

        # Campos de localização
        localizacao_endereco = request.form.get('localizacao_endereco', '')
        localizacao_cidade = request.form.get('localizacao_cidade', '')
        localizacao_estado = request.form.get('localizacao_estado', '')
        localizacao_cep = request.form.get('localizacao_cep', '')

        try:
            # Se nova categoria foi informada, criar/buscar categoria
            if nova_categoria and (not categoria_id or categoria_id == 'nova'):
                cursor.execute('INSERT OR IGNORE INTO categorias (nome) VALUES (%s)',
                               (nova_categoria, ))
                cursor.execute('SELECT id FROM categorias WHERE nome = %s',
                               (nova_categoria, ))
                categoria_result = cursor.fetchone()
                if categoria_result:
                    categoria_id = categoria_result[0]

            # Se usar endereço da empresa, buscar dados da empresa
            if usar_endereco_empresa:
                cursor.execute('SELECT endereco, cidade, estado, cep FROM empresas WHERE id = %s',
                               (session['empresa_id'], ))
                endereco_empresa = cursor.fetchone()
                if endereco_empresa:
                    localizacao_endereco = endereco_empresa[0] or localizacao_endereco
                    localizacao_cidade = endereco_empresa[1] or localizacao_cidade
                    localizacao_estado = endereco_empresa[2] or localizacao_estado
                    localizacao_cep = endereco_empresa[3] or localizacao_cep

            cursor.execute(
                '''
                UPDATE vagas
                SET titulo = %s, descricao = %s, requisitos = %s, salario_oferecido = %s, tipo_vaga = %s, diferenciais = %s,
                    categoria_id = %s, urgencia_contratacao = %s, data_congelamento_agendado = %s, usar_endereco_empresa = %s,
                    localizacao_endereco = %s, localizacao_cidade = %s, localizacao_estado = %s, localizacao_cep = %s
                WHERE id = %s
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
        WHERE v.id = %s
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

    return render_template('empresa/editar_vaga.html',
                           vaga=vaga,
                           categorias=categorias,
                           datetime=datetime,
                           timedelta=timedelta)


@app.route('/vaga/<int:vaga_id>')
def detalhes_vaga(vaga_id):
    if 'candidato_id' not in session:
        return redirect(url_for('login_candidato'))

    conn = get_db_connection()
    cursor = conn.cursor()

    # Buscar dados da vaga e empresa
    cursor.execute(
        '''
        SELECT v.*, e.nome as empresa_nome
        FROM vagas v
        JOIN empresas e ON v.empresa_id = e.id
        WHERE v.id = %s AND v.status = 'Ativa'
    ''', (vaga_id, ))

    vaga_data = cursor.fetchone()

    if not vaga_data:
        flash('Vaga não encontrada ou não está mais ativa', 'error')
        return redirect(url_for('dashboard_candidato'))

    # Verificar se já se candidatou
    cursor.execute(
        '''
        SELECT id, score FROM candidaturas
        WHERE candidato_id = %s AND vaga_id = %s
    ''', (session['candidato_id'], vaga_id))
    candidatura = cursor.fetchone()

    # Buscar dados do candidato para calcular feedback
    cursor.execute(
        '''
        SELECT resumo_profissional, endereco_completo, pretensao_salarial
        FROM candidatos WHERE id = %s
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

    # Calcular score se não candidatado ainda
    score = None

    if candidato_data:
        config = get_config()
        avaliador = get_avaliador(config['MODO_IA'])

        score = candidatura[1] if candidatura else avaliador.calcular_score(
            candidato_data[0], vaga['requisitos'], candidato_data[2],
            vaga['salario_oferecido'], vaga['diferenciais'], candidato_data[1],
            vaga['endereco_vaga'], vaga['tipo_vaga'])

    return render_template('detalhes_vaga.html',
                           vaga=vaga,
                           empresa=empresa,
                           score=score,
                           ja_candidatado=bool(candidatura))


@app.route('/candidato/minhas_candidaturas')
def minhas_candidaturas():
    if 'candidato_id' not in session:
        return redirect(url_for('login_candidato'))

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        '''
        SELECT v.id, v.titulo, e.nome as empresa_nome, v.salario_oferecido,
               ca.score, ca.posicao, ca.data_candidatura,
               DATE(ca.data_candidatura) as data_formatada
        FROM candidaturas ca
        JOIN vagas v ON ca.vaga_id = v.id
        JOIN empresas e ON v.empresa_id = e.id
        WHERE ca.candidato_id = %s
        ORDER BY ca.data_candidatura DESC
        ''', (session['candidato_id'], ))

    candidaturas = cursor.fetchall()
    conn.close()

    return render_template('candidato/minhas_candidaturas.html',
                           candidaturas=candidaturas)


@app.route('/baixar_curriculo/<int:candidato_id>')
def baixar_curriculo(candidato_id):
    if 'empresa_id' not in session:
        return redirect(url_for('login_empresa'))

    conn = get_db_connection()
    cursor = conn.cursor()

    # Verificar se a empresa tem acesso ao candidato (através de candidatura)
    cursor.execute(
        '''
        SELECT COUNT(*) FROM candidaturas ca
        JOIN vagas v ON ca.vaga_id = v.id
        WHERE ca.candidato_id = %s AND v.empresa_id = %s
    ''', (candidato_id, session['empresa_id']))

    if cursor.fetchone()[0] == 0:
        flash('Acesso negado ao currículo', 'error')
        return redirect(url_for('dashboard_empresa'))

    # Buscar dados do candidato
    cursor.execute(
        '''
        SELECT nome, caminho_curriculo
        FROM candidatos WHERE id = %s
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
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT id, titulo FROM vagas WHERE empresa_id = %s ORDER BY titulo',
        (empresa_id, ))
    vagas_disponiveis = cursor.fetchall()
    conn.close()

    from utils.relatorio_generator import gerar_dados_graficos
    dados_graficos = gerar_dados_graficos(empresa_id)

    return render_template('empresa/relatorio_empresa.html',
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
        return redirect(url_for('/empresa/relatorio_empresa'))


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

    conn = get_db_connection()
    cursor = conn.cursor()

    # Verificar se a candidatura existe
    cursor.execute(
        'SELECT id FROM candidaturas WHERE candidato_id = %s AND vaga_id = %s',
        (session['candidato_id'], vaga_id))
    candidatura = cursor.fetchone()

    if not candidatura:
        conn.close()
        return {'error': 'Candidatura não encontrada'}, 404

    # Remover candidatura
    cursor.execute(
        'DELETE FROM candidaturas WHERE candidato_id = %s AND vaga_id = %s',
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
        WHERE vaga_id = %s
    ''', (vaga_id, ))

    conn.commit()
    conn.close()

    return {'success': True}


@app.route("/reativar_vaga/<int:vaga_id>", methods=["POST"])
def reativar_vaga_route(vaga_id):
    if 'empresa_id' not in session:
        return jsonify({'error': 'Não autorizado'}), 401

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE vagas SET status = "Ativa" WHERE id = %s',
                   (vaga_id, ))
    conn.commit()
    conn.close()
    return redirect(url_for('/empresa/dashboard_empresa'))




from flask import jsonify, session
import mysql.connector
from datetime import datetime

@app.route('/api/notificacoes')
def api_notificacoes():
    """API para buscar notificações do candidato"""
    if 'candidato_id' not in session:
        return jsonify({'notificacoes': []})

    # Conectar ao banco MySQL
    conn = mysql.connector.connect(
        host='localhost',  # ou o host do seu banco de dados
        user='root',
        password='',
        database='recrutamentodb'
    )
    cursor = conn.cursor()

    try:
        # Verificar e criar colunas necessárias (executar apenas uma vez)
        cursor.execute("SHOW COLUMNS FROM notificacoes")
        columns = [column[0] for column in cursor.fetchall()]

        if 'tipo' not in columns:
            cursor.execute('ALTER TABLE notificacoes ADD COLUMN tipo TEXT DEFAULT "geral"')
            conn.commit()

        if 'titulo' not in columns:
            cursor.execute('ALTER TABLE notificacoes ADD COLUMN titulo TEXT DEFAULT ""')
            conn.commit()

        # Buscar notificações
        cursor.execute(
            '''
            SELECT n.id, n.candidato_id, IFNULL(n.tipo, 'geral') as tipo,
                   n.mensagem, IFNULL(n.lida, 0) as lida,
                   IFNULL(n.data_envio, NOW()) as data_criacao,
                   n.vaga_id, n.empresa_id, v.titulo as vaga_titulo, e.nome as empresa_nome
            FROM notificacoes n
            LEFT JOIN vagas v ON n.vaga_id = v.id
            LEFT JOIN empresas e ON n.empresa_id = e.id
            WHERE n.candidato_id = %s
            ORDER BY n.lida ASC, IFNULL(n.data_envio, NOW()) DESC
            LIMIT 50
        ''', (session['candidato_id'], ))

        emojis_tipo = {
            'contratacao': '🎉', 'vaga_congelada': '❄️', 'candidatura': '📋',
            'vaga_nova': '✨', 'alteracao_vaga': '🔔', 'vaga_excluida': '❌',
            'vaga_concluida': '✅', 'vaga_reativada': '🔄', 'geral': '📢'
        }

        notificacoes = []
        for row in cursor.fetchall():
            try:
                # Ajuste da data
                data_str = row[5]
                if isinstance(data_str, str) and 'T' in data_str:
                    data_criacao = datetime.fromisoformat(data_str.replace('Z', '+00:00'))
                else:
                    data_criacao = datetime.strptime(data_str, '%Y-%m-%d %H:%M:%S')
            except (ValueError, TypeError):
                data_criacao = datetime.now()

            dias_passados = (datetime.now() - data_criacao).days
            is_contratacao_recente = row[2] == 'contratacao' and dias_passados <= 30

            emoji = emojis_tipo.get(row[2], '📢')
            mensagem = row[3] or ''

            # Override emoji baseado no conteúdo
            if any(palavra in mensagem.upper() for palavra in ['PARABÉNS', 'CONTRATADO', 'SELECIONADO']):
                emoji = '🎉'
            elif 'congelada' in mensagem.lower():
                emoji = '❄️'
            elif any(palavra in mensagem.lower() for palavra in ['excluída', 'cancelada']):
                emoji = '❌'
            elif any(palavra in mensagem.lower() for palavra in ['atualizada', 'alterada']):
                emoji = '🔔'
            elif any(palavra in mensagem.lower() for palavra in ['reativada', 'retomada']):
                emoji = '🔄'

            # Construir título da notificação
            vaga_titulo = row[8]
            empresa_nome = row[9]
            if vaga_titulo and empresa_nome:
                titulo = f"{vaga_titulo} - {empresa_nome}"
            else:
                titulo = mensagem.split('\n')[0][:50] if mensagem else 'Notificação'

            notificacoes.append({
                'id': row[0],
                'tipo': row[2],
                'mensagem': mensagem,
                'data_criacao': data_criacao.strftime('%Y-%m-%d %H:%M:%S'),
                'lida': bool(row[4]),
                'emoji': emoji,
                'is_fixada': is_contratacao_recente,
                'titulo': titulo
            })

        return jsonify({'notificacoes': notificacoes, 'total': len(notificacoes)})

    except Exception as e:
        print(f"Erro na API de notificações: {e}")
        return jsonify({'notificacoes': [], 'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()
    



@app.route('/api/notificacoes/marcar-todas', methods=['POST'])
def marcar_todas_lidas():
    """API para marcar todas as notificações como lidas"""
    if 'candidato_id' not in session:
        return jsonify({'status': 'erro', 'mensagem': 'Não autenticado'}), 401

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE notificacoes SET lida = 1 WHERE candidato_id = %s",
                   (session['candidato_id'], ))
    conn.commit()
    conn.close()

    return jsonify({'status': 'ok'})


# Rota removida - já existe implementação acima

@app.route('/api/dicas-favoritas')
def obter_dicas_favoritas():
    candidato_id = session.get('candidato_id')
    if not candidato_id:
        return jsonify({'success': False, 'error': 'Não autorizado'}), 401

    try:
        conn = mysql.connect('recrutamentodb')
        cursor = conn.cursor()

        # Buscar vagas favoritas do candidato
        cursor.execute('''
            SELECT v.id, v.titulo, v.descricao, v.requisitos, v.salario_oferecido, 
                   v.tipo_vaga, e.nome as empresa_nome, f.data_adicao as data_favoritado
            FROM candidato_vaga_favorita f
            JOIN vagas v ON f.vaga_id = v.id
            JOIN empresas e ON v.empresa_id = e.id
            WHERE f.candidato_id = %s AND v.status = 'Ativa'
            ORDER BY f.data_adicao DESC
            LIMIT 10
        ''', (candidato_id,))

        vagas_favoritas = cursor.fetchall()

        if not vagas_favoritas:
            return jsonify({
                'success': False, 
                'message': 'Adicione vagas aos favoritos para receber dicas personalizadas'
            })

        # Buscar dados do candidato
        cursor.execute('''
            SELECT nome, email, competencias, experiencia, resumo_profissional, pretensao_salarial
            FROM candidatos 
            WHERE id = %s
        ''', (candidato_id,))

        candidato_data = cursor.fetchone()
        if not candidato_data:
            return jsonify({'success': False, 'error': 'Candidato não encontrado'}), 404

        # Gerar dicas baseadas nas vagas favoritas
        dicas = gerar_dicas_personalizadas(vagas_favoritas, candidato_data)

        return jsonify({
            'success': True,
            'dicas': dicas,
            'vagas_analisadas': len(vagas_favoritas)
        })

    except Exception as e:
        print(f"Erro ao gerar dicas favoritas: {e}")
        return jsonify({'success': False, 'error': 'Erro interno'}), 500
    finally:
        conn.close()

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
                        if len(palavra) > 3 and palavra not in ['para', 'com', 'das', 'dos', 'uma', 'ser', 'sua', 'seus', 'mais', 'pelo', 'pela', 'como', 'este', 'esta', 'você']]

    # Dica 1: Competências em alta
    if skills_demandadas:
        competencias_usuario = competencias.lower() if competencias else ''
        skills_faltando = [skill for skill in skills_demandadas[:5] 
                          if skill not in competencias_usuario]

        if skills_faltando:
            dicas.append({
                'categoria': 'competencias',
                'titulo': 'Competências em Alta Demanda',
                'descricao': f'As vagas que você favoritou frequentemente mencionam: {", ".join(skills_faltando[:3])}. Considere desenvolver essas habilidades.',
                'acao': f'Procure cursos online sobre "{skills_faltando[0]}" ou adicione projetos relacionados ao seu portfólio.'
            })

    # Dica 2: Faixa salarial
    if salarios:
        salario_medio = sum(salarios) / len(salarios)
        if pretensao_salarial and pretensao_salarial < salario_medio * 0.8:
            dicas.append({
                'categoria': 'negociacao',
                'titulo': 'Potencial de Negociação Salarial',
                'descricao': f'As vagas favoritas oferecem em média R$ {salario_medio:,.2f}, enquanto sua pretensão é R$ {pretensao_salarial:,.2f}.',
                'acao': 'Considere revisar sua pretensão salarial ou destacar mais suas qualificações para justificar um valor maior.'
            })

    # Dica 3: Modalidade de trabalho
    if tipos_vaga:
        tipo_mais_comum = max(set(tipos_vaga), key=tipos_vaga.count)
        dica_modalidade = {
            'categoria': 'preparacao',
            'titulo': f'Preparação para Trabalho {tipo_mais_comum}',
            'descricao': f'A maioria das suas vagas favoritas é do tipo {tipo_mais_comum}. Prepare-se adequadamente para essa modalidade.',
            'acao': ''
        }
        if tipo_mais_comum == "Remoto":
            dica_modalidade['acao'] = 'Configure um ambiente de trabalho adequado em casa, com boa conexão e ergonomia.'
        elif tipo_mais_comum == "Presencial":
            dica_modalidade['acao'] = 'Prepare-se para deslocamentos, horários presenciais e interações no escritório.'
        elif tipo_mais_comum == "Híbrido":
            dica_modalidade['acao'] = 'Organize-se para alternar entre home office e escritório, gerenciando bem seu tempo.'
        
        dicas.append(dica_modalidade)

    # Dica 4: Perfil profissional
    if not resumo_prof or len(resumo_prof) < 100:
        dicas.append({
            'categoria': 'perfil',
            'titulo': 'Melhore seu Resumo Profissional',
            'descricao': 'Um resumo profissional bem estruturado pode aumentar suas chances de ser notado.',
            'acao': 'Escreva um resumo de 2-3 parágrafos destacando suas principais conquistas, habilidades e objetivos profissionais.'
        })

    # Dica 5: Networking
    empresas_favoritas = list(set([vaga[6] for vaga in vagas_favoritas]))
    if len(empresas_favoritas) > 2:
        dicas.append({
            'categoria': 'networking',
            'titulo': 'Oportunidades de Networking',
            'descricao': f'Você demonstrou interesse em empresas como: {", ".join(empresas_favoritas[:3])}.',
            'acao': 'Pesquise profissionais dessas empresas no LinkedIn e tente estabelecer conexões relevantes.'
        })

    return dicas


@app.route('/api/notificacoes/marcar-lida', methods=['POST'])
def marcar_notificacao_lida():
    """API para marcar notificação individual como lida"""
    if 'candidato_id' not in session:
        return jsonify({'success': False, 'message': 'Acesso negado'})

    data = request.get_json()
    notificacao_id = data.get('id')

    if not notificacao_id:
        return jsonify({'error': 'ID da notificação é obrigatório'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        '''
        UPDATE notificacoes
        SET lida = 1
        WHERE id = %s AND candidato_id = %s
    ''', (notificacao_id, session['candidato_id']))

    conn.commit()
    conn.close()

    return jsonify({'success': True})


@app.route('/api/notificacoes/marcar-todas-lidas', methods=['PUT'])
def marcar_todas_notificacoes_lidas():
    """API para marcar todas as notificações como lidas"""
    if 'candidato_id' not in session:
        return jsonify({'success': False, 'message': 'Acesso negado'})

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        '''
        UPDATE notificacoes
        SET lida = 1
        WHERE candidato_id = %s
    ''', (session['candidato_id'], ))

    conn.commit()
    conn.close()

    return jsonify({'success': True})


@app.route('/api/notificacoes/<int:notificacao_id>/lida', methods=['PUT'])
def marcar_notificacao_individual_lida(notificacao_id):
    """API para marcar uma notificação específica como lida"""
    if 'candidato_id' not in session:
        return jsonify({'success': False, 'message': 'Acesso negado'})

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        '''
        UPDATE notificacoes
        SET lida = 1
        WHERE id = %s AND candidato_id = %s
    ''', (notificacao_id, session['candidato_id']))

    conn.commit()
    conn.close()

    return jsonify({'success': True})


@app.route('/api/notificacoes/limpar-todas', methods=['DELETE'])
def limpar_todas_notificacoes():
    """API para limpar todas as notificações"""
    if 'candidato_id' not in session:
        return jsonify({'success': False, 'message': 'Acesso negado'})

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('DELETE FROM notificacoes WHERE candidato_id = %s',
                   (session['candidato_id'], ))
    conn.commit()
    conn.close()

    return jsonify({'success': True})





@app.route('/api/notificacoes/demo', methods=['POST'])
def criar_notificacoes_demo():
    """API para criar notificações de demonstração"""
    if 'candidato_id' not in session:
        return jsonify({'success': False, 'message': 'Acesso negado'})

    # Conectar ao banco MySQL
    conn = mysql.connector.connect(
        host='localhost',
        user='root',
        password='',
        database='recrutamentodb'
    )
    cursor = conn.cursor()

    # Criar notificações de demo
    notificacoes_demo = [
        ('🎉 Parabéns! Você foi selecionado para a vaga de Desenvolvedor Python na TechCorp!', 'contratacao'),
        ('📋 Nova candidatura registrada para vaga de Data Scientist', 'candidatura'),
        ('✨ Nova vaga disponível que pode interessar: Analista de Sistemas', 'vaga_nova'),
        ('🔔 A vaga de Frontend Developer foi atualizada com novos requisitos', 'alteracao_vaga'),
        ('❄️ A vaga de DevOps Engineer foi temporariamente congelada', 'vaga_congelada'),
    ]

    for mensagem, tipo in notificacoes_demo:
        # Remover o campo 'data_envio', pois o MySQL vai preencher automaticamente
        cursor.execute(
            '''
            INSERT INTO notificacoes (candidato_id, mensagem, tipo, lida, titulo)
            VALUES (%s, %s, %s, 0, %s)
        ''', (session['candidato_id'], mensagem, tipo, mensagem[:255]))  # Título: uma versão curta da mensagem

    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({
        'success': True,
        'message': 'Notificações de demo criadas!'
    })



@app.route('/api/notificacoes/<int:notificacao_id>/apagar', methods=['DELETE'])
def apagar_notificacao(notificacao_id):
    """API para apagar uma notificação específica"""
    if 'candidato_id' not in session:
        return jsonify({'error': 'Não autorizado'}), 401

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        '''
        DELETE FROM notificacoes
        WHERE id = %s AND candidato_id = %s
    ''', (notificacao_id, session['candidato_id']))

    conn.commit()
    sucesso = cursor.rowcount > 0
    conn.close()

    return jsonify({'success': sucesso})


@app.route('/api/notificacoes/apagar-todas', methods=['DELETE'])
def apagar_todas_notificacoes():
    """API para apagar todas as notificações"""
    if 'candidato_id' not in session:
        return jsonify({'error': 'Não autorizado'}), 401

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        '''
        DELETE FROM notificacoes
        WHERE candidato_id = %s
    ''', (session['candidato_id'], ))

    conn.commit()
    count = cursor.rowcount
    conn.close()

    return jsonify({'success': True, 'deleted_count': count})


@app.route('/debug/candidatos')
def debug_candidatos():
    """Rota de debug para listar todos os candidatos"""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('SELECT id, nome, email FROM candidatos ORDER BY id')
        candidatos = cursor.fetchall()

        result = "<h2>Lista de Candidatos:</h2><ul>"
        for candidato in candidatos:
            result += f"<li>ID: {candidato[0]} - Nome: {candidato[1]} - Email: {candidato[2]}</li>"
        result += "</ul>"

        # Contar notificações por candidato
        result += "<h2>Notificações por Candidato:</h2><ul>"
        cursor.execute('''
            SELECT n.candidato_id, COUNT(*) as total, 
                   SUM(CASE WHEN n.lida = 0 THEN 1 ELSE 0 END) as nao_lidas,
                   c.nome
            FROM notificacoes n
            JOIN candidatos c ON n.candidato_id = c.id
            GROUP BY n.candidato_id, c.nome
            ORDER BY n.candidato_id
        ''')

        notif_stats = cursor.fetchall()
        for stat in notif_stats:
            result += f"<li>Candidato {stat[0]} ({stat[3]}): {stat[1]} total, {stat[2]} não lidas</li>"
        result += "</ul>"

        return result

    except Exception as e:
        return f"Erro: {str(e)}"
    finally:
        conn.close()


@app.route('/debug/testar-notificacao/<int:candidato_id>')
def debug_testar_notificacao(candidato_id):
    """Rota de debug para testar notificação em candidato específico"""
    try:
        mensagem = f"🧪 Teste de notificação para candidato {candidato_id} - {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"

        sucesso = notification_system.criar_notificacao(
            candidato_id, mensagem, None, None, 'teste')

        return jsonify({
            'candidato_id': candidato_id,
            'sucesso': sucesso,
            'mensagem': mensagem,
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        return jsonify({'error': str(e), 'candidato_id': candidato_id})


@app.route('/debug/notificacoes-sistema')
def debug_notificacoes_sistema_route():
    """Rota de debug para analisar sistema de notificações"""
    try:
        from utils.notifications import debug_notificacoes_sistema
        debug_notificacoes_sistema()

        conn = get_db_connection()
        cursor = conn.cursor()

        # Dados para retorno
        cursor.execute('SELECT id, nome, email FROM candidatos ORDER BY id')
        candidatos = cursor.fetchall()

        cursor.execute('''
            SELECT n.candidato_id, COUNT(*) as total, 
                   SUM(CASE WHEN n.lida = 0 THEN 1 ELSE 0 END) as nao_lidas,
                   c.nome
            FROM notificacoes n
            JOIN candidatos c ON n.candidato_id = c.id
            GROUP BY n.candidato_id, c.nome
            ORDER BY n.candidato_id
        ''')
        stats = cursor.fetchall()

        conn.close()

        return jsonify({
            'candidatos': [{'id': c[0], 'nome': c[1], 'email': c[2]} for c in candidatos],
            'estatisticas': [{'candidato_id': s[0], 'total': s[1], 'nao_lidas': s[2], 'nome': s[3]} for s in stats],
            'total_candidatos': len(candidatos),
            'candidatos_com_notificacoes': len(stats)
        })

    except Exception as e:
        return jsonify({'error': str(e)})


@app.route('/debug/testar-todas-notificacoes')
def debug_testar_todas_notificacoes():
    """Rota para testar notificações em todos os candidatos"""
    try:
        from utils.notifications import testar_notificacao_para_todos
        sucesso = testar_notificacao_para_todos()

        return jsonify({
            'success': sucesso,
            'message': 'Teste de notificações concluído',
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        return jsonify({'error': str(e)})



@app.route('/api/notificacoes/nao-lidas')
def api_notificacoes_nao_lidas():
    """API para contar notifications não lidas"""
    if 'candidato_id' not in session:
        return jsonify({'count': 0})

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM notificacoes WHERE candidato_id = %s AND lida = 0",
                   (session['candidato_id'],))
    count = cursor.fetchone()[0]

    return jsonify({'count': count})


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

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            'SELECT endereco, cidade, estado, cep FROM empresas WHERE id = %s',
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
    """API para adicionar/remover vaga dos favoritos"""
    if 'candidato_id' not in session:
        return jsonify({'error': 'Não autorizado', 'favorited': False}), 401

    data = request.get_json()
    if not data or 'vaga_id' not in data:
        return jsonify({'error': 'ID da vaga é obrigatório', 'favorited': False}), 400

    candidato_id = session['candidato_id']
    vaga_id = data['vaga_id']

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Verificar se já existe nos favoritos
        cursor.execute(
            'SELECT id FROM candidato_vaga_favorita WHERE candidato_id = %s AND vaga_id = %s',
            (candidato_id, vaga_id)
        )
        favorito_existente = cursor.fetchone()

        if favorito_existente:
            # Remover dos favoritos
            cursor.execute(
                'DELETE FROM candidato_vaga_favorita WHERE candidato_id = %s AND vaga_id = %s',
                (candidato_id, vaga_id)
            )
            favorited = False
            action = 'removida'
        else:
            # Adicionar aos favoritos
            cursor.execute(
                'INSERT INTO candidato_vaga_favorita (candidato_id, vaga_id, data_adicao) VALUES (%s, %s, datetime("now"))',
                (candidato_id, vaga_id)
            )
            favorited = True
            action = 'adicionada'

        conn.commit()
        return jsonify({
            'success': True,
            'favorited': favorited,
            'message': f'Vaga {action} dos favoritos com sucesso!'
        })

    except Exception as e:
        conn.rollback()
        return jsonify({
            'error': f'Erro ao atualizar favoritos: {str(e)}',
            'favorited': False
        }), 500
    finally:
        conn.close()


@app.route('/api/vagas-empresa')
def api_vagas_empresa():
    """API para buscar vagas da empresa para filtros"""
    if 'empresa_id' not in session:
        return jsonify({'error': 'Não autorizado'}), 401

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('SELECT id, titulo, status FROM vagas WHERE empresa_id = %s ORDER BY titulo',
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

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        empresa_id = session['empresa_id']

        # Verificar se a empresa tem acesso ao candidato (através de candidatura)
        cursor.execute(
            '''
            SELECT c.vaga_id FROM candidaturas c
            JOIN vagas v ON c.vaga_id = v.id
            WHERE c.candidato_id = %s AND v.empresa_id = %s AND c.vaga_id = %s
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
            WHERE empresa_id = %s AND candidato_id = %s AND vaga_id = %s
        ''', (empresa_id, candidato_id, vaga_id))

        ja_favoritado = cursor.fetchone() is not None

        if acao == 'toggle' or (acao == 'add' and not ja_favoritado):
            if ja_favoritado:
                # Remover dos favoritos
                cursor.execute(
                    '''
                    DELETE FROM empresa_candidato_favorito
                    WHERE empresa_id = %s AND candidato_id = %s AND vaga_id = %s
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
                    VALUES (%s, %s, %s)
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
                WHERE empresa_id = %s AND candidato_id = %s AND vaga_id = %s
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

    conn = mysql.connect('recrutamentodb')
    cursor = conn.cursor()

    try:
        # Garantir que as tabelas existem
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS empresa_favorito_candidato_geral (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                empresa_id INTEGER NOT NULL,
                candidato_id INTEGER NOT NULL,
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (empresa_id) REFERENCES empresas (id),
                FOREIGN KEY (candidato_id) REFERENCES candidatos (id),
                UNIQUE(empresa_id, candidato_id)
            )
        ''')

        cursor.execute('''
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
        ''')

        empresa_id = session['empresa_id']

        # Buscar candidatos favoritos gerais
        cursor.execute(
            '''
            SELECT DISTINCT c.id, c.nome, c.email, c.telefone, c.linkedin,
                   'Favorito Geral' as vaga_titulo, 0 as vaga_id,
                   0 as score, 0 as posicao,
                   efcg.data_criacao as data_favorito
            FROM empresa_favorito_candidato_geral efcg
            JOIN candidatos c ON efcg.candidato_id = c.id
            WHERE efcg.empresa_id = %s

            UNION

            SELECT DISTINCT c.id, c.nome, c.email, c.telefone, c.linkedin,
                   v.titulo as vaga_titulo, v.id as vaga_id,
                   COALESCE(ca.score, 0) as score, COALESCE(ca.posicao, 0) as posicao,
                   ecf.data_criacao as data_favorito
            FROM empresa_candidato_favorito ecf
            JOIN candidatos c ON ecf.candidato_id = c.id
            JOIN vagas v ON ecf.vaga_id = v.id
            LEFT JOIN candidaturas ca ON ca.candidato_id = c.id AND ca.vaga_id = v.id
            WHERE ecf.empresa_id = %s

            ORDER BY data_favorito DESC
        ''', (empresa_id, empresa_id))

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
                'posicao': row[8] if row[8] else 0,
                'data_favorito': row[9]
            })

        return jsonify(favoritos)

    except Exception as e:
        print(f"Erro na API candidatos-favoritos: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()


@app.route('/empresa/candidatos-geral')
def candidatos_geral():
    """Página para visualizar todos os candidatos cadastrados"""
    if 'empresa_id' not in session:
        return redirect(url_for('login_empresa'))

    return render_template('empresa/candidatos_geral.html')


@app.route('/api/score-detalhes/<int:candidato_id>/<int:vaga_id>')
def api_score_detalhes(candidato_id, vaga_id):
    """API para obter detalhes do cálculo do score"""
    if 'empresa_id' not in session:
        return jsonify({'error': 'Não autorizado'}), 401

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Verificar se a empresa tem acesso ao candidato
        cursor.execute(
            '''
            SELECT c.resumo_profissional, c.pretensao_salarial, c.endereco_completo,
                   v.requisitos, v.salario_oferecido, v.diferenciais, v.tipo_vaga, v.endereco_vaga
            FROM candidatos c, vagas v
            WHERE c.id = %s AND v.id = %s AND v.empresa_id = %s
        ''', (candidato_id, vaga_id, session['empresa_id']))

        resultado = cursor.fetchone()
        if not resultado:
            return jsonify({'error': 'Dados não encontrados'}), 404

        curriculo, pretensao_salarial, candidato_endereco, requisitos, salario_oferecido, diferenciais, tipo_vaga, vaga_endereco = resultado

        # Calcular score detalhado
        config = get_config()
        avaliador = get_avaliador(config['MODO_IA'])

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
            'salarial':
            round(score_salarial, 1),
            'requisitos':
            round(score_requisitos, 1),
            'experiencia':
            round(score_experiencia, 1),
            'diferenciais':
            round(score_diferenciais, 1),
            'localizacao':
            round(score_localizacao, 1),
            'formacao':
            round(score_formacao, 1),
            'explicacao_salarial':
            gerar_explicacao_salarial(pretensao_salarial, salario_oferecido),
            'explicacao_requisitos':
            gerar_explicacao_requisitos(curriculo, requisitos),
            'explicacao_experiencia':
            gerar_explicacao_experiencia(curriculo),
            'explicacao_diferenciais':
            'Baseado em certificações e habilidades extras identificadas',
            'explicacao_localizacao':
            gerar_explicacao_localizacao(candidato_endereco, vaga_endereco,
                                         tipo_vaga),
            'explicacao_formacao':
            gerar_explicacao_formacao(curriculo, requisitos)
        }

        return jsonify(detalhes)

    except Exception as e:
        return jsonify({'error': str(e)}), 500
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
           for palavra in ['senior', 'sênior', 'líder', 'lead']):
        return "Perfil Senior identificado"
    elif any(palavra in curriculo_lower for palavra in ['pleno', 'analista']):
        return "Perfil Pleno identificado"
    elif any(palavra in curriculo_lower
             for palavra in ['junior', 'júnior', 'estagiário']):
        return "Perfil Junior identificado"
    else:
        return "Nível de experiência baseado no histórico profissional"


def gerar_explicacao_localizacao(candidato_endereco, vaga_endereco, tipo_vaga):
    """Gera explicação para o score de localização"""
    if tipo_vaga == 'Remota':
        return "Vaga remota - localização não é fator limitante"

    if not candidato_endereco or not vaga_endereco:
        return "Dados de localização insuficientes"

    if candidato_endereco.lower() in vaga_endereco.lower(
    ) or vaga_endereco.lower() in candidato_endereco.lower():
        return "Localização muito compatível"
    else:
        return f"Localização para vaga {tipo_vaga.lower()}"


def gerar_explicacao_formacao(curriculo, requisitos):
    """Gera explicação para o score de formação"""
    if not curriculo:
        return "Dados de formação não disponíveis"

    curriculo_lower = curriculo.lower()

    if any(form in curriculo_lower
           for form in ['mestrado', 'doutorado', 'phd']):
        return "Pós-graduação stricto sensu identificada"
    elif any(form in curriculo_lower
             for form in ['mba', 'especialização', 'pós-graduação']):
        return "Pós-graduação lato sensu identificada"
    elif any(form in curriculo_lower
             for form in ['graduação', 'bacharelado', 'licenciatura']):
        return "Ensino superior completo"
    else:
        return "Formação baseada no perfil profissional"


@app.route('/api/candidatos-geral')
def api_candidatos_geral():
    """API para listar todos os candidatos cadastrados"""
    if 'empresa_id' not in session:
        return jsonify({'error': 'Não autorizado'}), 401

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Criar tabela de favoritos se não existir (MySQL)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS empresa_favorito_candidato_geral (
                id INT AUTO_INCREMENT PRIMARY KEY,
                empresa_id INT NOT NULL,
                candidato_id INT NOT NULL,
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (empresa_id) REFERENCES empresas(id),
                FOREIGN KEY (candidato_id) REFERENCES candidatos(id),
                UNIQUE KEY(empresa_id, candidato_id)
            )
        ''')
        conn.commit()

        # Garantir que a coluna data_cadastro exista
        cursor.execute("SHOW COLUMNS FROM candidatos LIKE 'data_cadastro'")
        col_exists = cursor.fetchone()
        if not col_exists:
            cursor.execute("""
                ALTER TABLE candidatos 
                ADD COLUMN data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            """)
            conn.commit()

        empresa_id = session['empresa_id']

        # Buscar candidatos
        cursor.execute('''
            SELECT DISTINCT 
                c.id, c.nome, c.email, c.telefone, c.linkedin,
                c.endereco_completo, c.pretensao_salarial, c.competencias,
                c.resumo_profissional, 
                COALESCE(c.data_cadastro, NOW()) as data_cadastro,
                CASE WHEN c.resumo_profissional IS NOT NULL AND c.resumo_profissional != '' THEN 1 ELSE 0 END as tem_curriculo,
                CASE WHEN efcg.candidato_id IS NOT NULL THEN 1 ELSE 0 END as is_favorito
            FROM candidatos c
            LEFT JOIN empresa_favorito_candidato_geral efcg 
                   ON efcg.candidato_id = c.id AND efcg.empresa_id = %s
            ORDER BY COALESCE(c.data_cadastro, NOW()) DESC
        ''', (empresa_id,))

        candidatos = []
        for row in cursor.fetchall():
            candidatos.append({
                'id': row['id'],
                'nome': row['nome'] or '',
                'email': row['email'] or '',
                'telefone': row['telefone'] or '',
                'linkedin': row['linkedin'] or '',
                'endereco_completo': row['endereco_completo'] or '',
                'pretensao_salarial': row['pretensao_salarial'] or 0,
                'competencias': row['competencias'] or '',
                'resumo_profissional': row['resumo_profissional'] or '',
                'data_cadastro': str(row['data_cadastro']) if row['data_cadastro'] else '',
                'tem_curriculo': bool(row['tem_curriculo']),
                'is_favorito': bool(row['is_favorito'])
            })

        return jsonify(candidatos)

    except Exception as e:
        print(f"Erro na API candidatos-geral: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/api/favoritar-candidato-geral', methods=['POST'])
def favoritar_candidato_geral():
    """API para empresa favoritar/desfavoritar candidato geral"""
    if 'empresa_id' not in session:
        return jsonify({'success': False, 'message': 'Não autorizado'}), 401

    data = request.get_json()
    candidato_id = data.get('candidato_id')
    acao = data.get('acao', 'toggle')

    if not candidato_id:
        return jsonify({
            'success': False,
            'message': 'Candidato ID obrigatório'
        }), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Garantir que a tabela existe
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS empresa_favorito_candidato_geral (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                empresa_id INTEGER NOT NULL,
                candidato_id INTEGER NOT NULL,
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (empresa_id) REFERENCES empresas (id),
                FOREIGN KEY (candidato_id) REFERENCES candidatos (id),
                UNIQUE(empresa_id, candidato_id)
            )
        ''')

        empresa_id = session['empresa_id']

        # Verificar se o candidato existe
        cursor.execute('SELECT id FROM candidatos WHERE id = %s',
                       (candidato_id, ))
        if not cursor.fetchone():
            return jsonify({
                'success': False,
                'message': 'Candidato não encontrado'
            }), 404

        # Verificar se já está favoritado
        cursor.execute(
            '''
            SELECT id FROM empresa_favorito_candidato_geral
            WHERE empresa_id = %s AND candidato_id = %s
        ''', (empresa_id, candidato_id))

        ja_favoritado = cursor.fetchone() is not None

        if acao == 'toggle' or (acao == 'add' and not ja_favoritado):
            if ja_favoritado:
                # Remover dos favoritos
                cursor.execute(
                    '''
                    DELETE FROM empresa_favorito_candidato_geral
                    WHERE empresa_id = %s AND candidato_id = %s
                ''', (empresa_id, candidato_id))
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
                    INSERT INTO empresa_favorito_candidato_geral (empresa_id, candidato_id)
                    VALUES (%s, %s)
                ''', (empresa_id, candidato_id))
                conn.commit()
                return jsonify({
                    'success': True,
                    'favorited': True,
                    'message': 'Candidato adicionado aos favoritos'
                })

        elif acao == 'remove' and ja_favoritado:
            cursor.execute(
                '''
                DELETE FROM empresa_favorito_candidato_geral
                WHERE empresa_id = %s AND candidato_id = %s
            ''', (empresa_id, candidato_id))
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
        print(f"Erro ao favoritar candidato geral: {e}")
        return jsonify({'success': False, 'message': f'Erro: {str(e)}'}), 500
    finally:
        conn.close()


@app.route("/empresa/candidatos-favoritos")
def candidatos_favoritos():
    """Página para visualizar candidatos favoritos"""
    if 'empresa_id' not in session:
        return redirect(url_for('login_empresa'))

    return render_template('empresa/candidatos_favoritos.html')

@app.route('/api/todas-vagas')
def api_todas_vagas():
    """API para buscar todas as vagas disponíveis para o candidato"""
    if 'candidato_id' not in session:
        return jsonify({'error': 'Não autorizado'}), 401

    conn = get_db_connection()
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
            LEFT JOIN candidato_vaga_favorita cvf ON cvf.candidato_id = %s AND cvf.vaga_id = v.id
            LEFT JOIN candidaturas ca ON ca.candidato_id = %s AND ca.vaga_id = v.id
            WHERE v.status = 'Ativa'
            ORDER BY v.data_criacao DESC
        ''', (session['candidato_id'], session['candidato_id']))

        vagas_raw = cursor.fetchall()

        # Buscar informações do candidato para calcular scores
        cursor.execute(
            'SELECT pretensao_salarial, resumo_profissional, endereco_completo FROM candidatos WHERE id = %s',
            (session['candidato_id'], ))
        candidato_info = cursor.fetchone()

        conn.close()

        if not candidato_info:
            return jsonify({'error': 'Candidato não encontrado'}), 404

        # Calcular scores
        config = get_config()
        avaliador = get_avaliador(config['MODO_IA'])
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
                'score':
                float(score)
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

    conn = get_db_connection()
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

    conn = get_db_connection()
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
            LEFT JOIN candidato_vaga_favorita cvf ON cvf.candidato_id = %s AND cvf.vaga_id = v.id
            LEFT JOIN candidaturas ca ON ca.candidato_id = %s AND ca.vaga_id = v.id
            LEFT JOIN categorias c ON v.categoria_id = c.id
            WHERE v.status = 'Ativa'
        '''

        params = [session['candidato_id'], session['candidato_id']]

        # Adicionar filtros
        if keyword:
            query_base += ' AND (v.titulo LIKE %s OR v.descricao LIKE %s OR v.requisitos LIKE %s)'
            keyword_param = f'%{keyword}%'
            params.extend([keyword_param, keyword_param, keyword_param])

        if location:
            query_base += ' AND (v.localizacao_cidade LIKE %s OR v.localizacao_estado LIKE %s)'
            location_param = f'%{location}%'
            params.extend([location_param, location_param])

        if category:
            query_base += ' AND v.categoria_id = %s'
            params.append(category)

        if urgency:
            query_base += ' AND v.urgencia_contratacao = %s'
            params.append(urgency)

        if salary:
            try:
                salary_value = float(salary)
                query_base += ' AND v.salario_oferecido >= %s'
                params.append(salary_value)
            except ValueError:
                pass

        if job_type:
            query_base += ' AND v.tipo_vaga = %s'
            params.append(job_type)

        query_base += ' ORDER BY v.data_criacao DESC'

        cursor.execute(query_base, params)
        vagas_raw = cursor.fetchall()

        # Buscar informações do candidato para calcular scores
        cursor.execute(
            'SELECT pretensao_salarial, resumo_profissional, endereco_completo FROM candidatos WHERE id = %s',
            (session['candidato_id'], ))
        candidato_info = cursor.fetchone()

        if not candidato_info:
            return jsonify({'error': 'Candidato não encontrado'}), 404

        # Calcular scores
        config = get_config()
        avaliador = get_avaliador(config['MODO_IA'])
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


# =========================
# ROTAS DO ASSISTENTE IA
# =========================


@app.route('/api/ia/analisar-curriculo')
def api_analisar_curriculo():
    """API para análise IA do currículo do candidato"""
    if 'candidato_id' not in session:
        return jsonify({'error': 'Não autorizado'}), 401

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        candidato_id = session['candidato_id']

        # Buscar currículo do candidato
        cursor.execute('SELECT resumo_profissional FROM candidatos WHERE id = %s',
                       (candidato_id, ))
        resultado = cursor.fetchone()

        if not resultado or not resultado[0]:
            return jsonify({'error': 'Currículo não encontrado'}), 404

        curriculo_texto = resultado[0]

        # Analisar currículo com IA
        analise = get_ia_assistant().analisar_curriculo(candidato_id,
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

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        candidato_id = session['candidato_id']

        # Buscar currículo do candidato
        cursor.execute('SELECT resumo_profissional FROM candidatos WHERE id = %s',
                       (candidato_id, ))
        resultado = cursor.fetchone()

        if not resultado or not resultado[0]:
            return jsonify({'error': 'Currículo não encontrado'}), 404

        curriculo_texto = resultado[0]

        # Obter recomendações da IA
        recomendacoes = get_ia_assistant().recomendar_vagas_personalizadas(
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

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        candidato_id = session['candidato_id']

        # Buscar dados do candidato e da vaga
        cursor.execute(
            '''
            SELECT c.resumo_profissional, v.requisitos, v.salario_oferecido
            FROM candidatos c, vagas v
            WHERE c.id = %s AND v.id = %s AND v.status = 'Ativa'
        ''', (candidato_id, vaga_id))

        resultado = cursor.fetchone()

        if not resultado:
            return jsonify({'error': 'Dados não encontrados'}), 404

        curriculo_texto, requisitos_vaga, salario_vaga = resultado

        # Gerar dicas da IA
        dicas = get_ia_assistant().gerar_dicas_melhoria_vaga(curriculo_texto,
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

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        candidato_id = session['candidato_id']

        # Buscar dados do candidato
        cursor.execute(
            'SELECT nome, email FROM candidatos WHERE id = %s',
            (candidato_id, ))
        resultado = cursor.fetchone()

        if not resultado:
            return jsonify({'error': 'Candidato não encontrado'}), 404

        candidato_nome, candidato_email, curriculo_texto = resultado

        # Obter análise e recomendações
        analise = get_ia_assistant().analisar_curriculo(candidato_id,
                                                         curriculo_texto)
        recomendacoes = get_ia_assistant().recomendar_vagas_personalizadas(
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


if __name__ == '__main__':
    inicializar_banco()

    # Iniciar scheduler em background
    try:
        iniciar_scheduler_background()
        print("Sistema de agendamento iniciado com sucesso!")
    except Exception as e:
        print(f"Erro ao iniciar scheduler: {e}")

    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)


# =========================
# API DE FAVORITOS
# =========================

@app.route('/api/favoritos/toggle', methods=['POST'])
def api_toggle_favorito():
    """API para adicionar/remover vaga dos favoritos"""
    if 'candidato_id' not in session:
        return jsonify({'error': 'Não autorizado', 'favorited': False}), 401

    data = request.get_json()
    if not data or 'vaga_id' not in data:
        return jsonify({'error': 'ID da vaga é obrigatório', 'favorited': False}), 400

    candidato_id = session['candidato_id']
    vaga_id = data['vaga_id']

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Verificar se já existe nos favoritos
        cursor.execute(
            'SELECT id FROM candidato_vaga_favorita WHERE candidato_id = %s AND vaga_id = %s',
            (candidato_id, vaga_id)
        )
        favorito_existente = cursor.fetchone()

        if favorito_existente:
            # Remover dos favoritos
            cursor.execute(
                'DELETE FROM candidato_vaga_favorita WHERE candidato_id = %s AND vaga_id = %s',
                (candidato_id, vaga_id)
            )
            favorited = False
            action = 'removida'
        else:
            # Adicionar aos favoritos
            cursor.execute(
                'INSERT INTO candidato_vaga_favorita (candidato_id, vaga_id, data_adicao) VALUES (%s, %s, datetime("now"))',
                (candidato_id, vaga_id)
            )
            favorited = True
            action = 'adicionada'

        conn.commit()
        return jsonify({
            'success': True,
            'favorited': favorited,
            'message': f'Vaga {action} dos favoritos com sucesso!'
        })

    except Exception as e:
        conn.rollback()
        return jsonify({
            'error': f'Erro ao atualizar favoritos: {str(e)}',
            'favorited': False
        }), 500
    finally:
        conn.close()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000, use_reloader=False)

