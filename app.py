
import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from utils.helpers import inicializar_banco
from utils.resume_extractor import processar_upload_curriculo, finalizar_processamento_curriculo
from avaliador import criar_avaliador
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'chave-secreta-mvp-recrutamento'

# Configurações do ambiente
MODO_IA = os.getenv('MODO_IA', 'local')
TOP_JOBS = int(os.getenv('TOP_JOBS', '3'))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login_empresa', methods=['GET', 'POST'])
def login_empresa():
    if request.method == 'POST':
        cnpj = request.form['cnpj']
        senha = request.form['senha']
        
        conn = sqlite3.connect('recrutamento.db')
        cursor = conn.cursor()
        
        cursor.execute('SELECT id, senha_hash FROM empresas WHERE cnpj = ?', (cnpj,))
        empresa = cursor.fetchone()
        conn.close()
        
        if empresa and check_password_hash(empresa[1], senha):
            session['empresa_id'] = empresa[0]
            session['tipo_usuario'] = 'empresa'
            return redirect(url_for('dashboard_empresa'))
        else:
            flash('CNPJ ou senha incorretos', 'error')
    
    return render_template('login_empresa.html')

@app.route('/cadastro_empresa', methods=['GET', 'POST'])
def cadastro_empresa():
    if request.method == 'POST':
        cnpj = request.form['cnpj']
        nome = request.form['nome']
        email = request.form['email']
        senha = request.form['senha']
        
        conn = sqlite3.connect('recrutamento.db')
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO empresas (cnpj, nome, email, senha_hash)
                VALUES (?, ?, ?, ?)
            ''', (cnpj, nome, email, generate_password_hash(senha)))
            conn.commit()
            flash('Empresa cadastrada com sucesso!', 'success')
            return redirect(url_for('login_empresa'))
        except sqlite3.IntegrityError:
            flash('CNPJ já cadastrado', 'error')
        finally:
            conn.close()
    
    return render_template('cadastro_empresa.html')

@app.route('/login_candidato', methods=['GET', 'POST'])
def login_candidato():
    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['senha']
        
        conn = sqlite3.connect('recrutamento.db')
        cursor = conn.cursor()
        
        cursor.execute('SELECT id, senha_hash FROM candidatos WHERE email = ?', (email,))
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
        pretensao_salarial = float(request.form['pretensao_salarial'])
        
        conn = sqlite3.connect('recrutamento.db')
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO candidatos (nome, email, senha_hash, telefone, linkedin, pretensao_salarial)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (nome, email, generate_password_hash(senha), telefone, linkedin, pretensao_salarial))
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
    if 'empresa_id' not in session:
        return redirect(url_for('login_empresa'))
    
    conn = sqlite3.connect('recrutamento.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM vagas WHERE empresa_id = ?', (session['empresa_id'],))
    vagas = cursor.fetchall()
    conn.close()
    
    return render_template('dashboard_empresa.html', vagas=vagas)

@app.route('/criar_vaga', methods=['GET', 'POST'])
def criar_vaga():
    if 'empresa_id' not in session:
        return redirect(url_for('login_empresa'))
    
    if request.method == 'POST':
        titulo = request.form['titulo']
        descricao = request.form['descricao']
        requisitos = request.form['requisitos']
        salario_oferecido = float(request.form['salario_oferecido'])
        
        conn = sqlite3.connect('recrutamento.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO vagas (empresa_id, titulo, descricao, requisitos, salario_oferecido)
            VALUES (?, ?, ?, ?, ?)
        ''', (session['empresa_id'], titulo, descricao, requisitos, salario_oferecido))
        conn.commit()
        conn.close()
        
        flash('Vaga criada com sucesso!', 'success')
        return redirect(url_for('dashboard_empresa'))
    
    return render_template('criar_vaga.html')

@app.route('/candidatos_vaga/<int:vaga_id>')
def candidatos_vaga(vaga_id):
    if 'empresa_id' not in session:
        return redirect(url_for('login_empresa'))
    
    conn = sqlite3.connect('recrutamento.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT c.nome, c.email, c.telefone, c.linkedin, ca.score, ca.posicao
        FROM candidaturas ca
        JOIN candidatos c ON ca.candidato_id = c.id
        WHERE ca.vaga_id = ?
        ORDER BY ca.score DESC
    ''', (vaga_id,))
    
    candidatos = cursor.fetchall()
    
    cursor.execute('SELECT titulo FROM vagas WHERE id = ?', (vaga_id,))
    vaga = cursor.fetchone()
    conn.close()
    
    return render_template('candidatos_vaga.html', candidatos=candidatos, vaga_titulo=vaga[0] if vaga else '')

@app.route('/dashboard_candidato')
def dashboard_candidato():
    if 'candidato_id' not in session:
        return redirect(url_for('login_candidato'))
    
    conn = sqlite3.connect('recrutamento.db')
    cursor = conn.cursor()
    
    # Verificar se tem currículo
    cursor.execute('SELECT texto_curriculo FROM candidatos WHERE id = ?', (session['candidato_id'],))
    candidato = cursor.fetchone()
    
    if not candidato or not candidato[0]:
        conn.close()
        return redirect(url_for('upload_curriculo'))
    
    # Buscar vagas onde já se candidatou
    cursor.execute('''
        SELECT v.id, v.titulo, e.nome as empresa_nome, v.salario_oferecido,
               ca.score, ca.posicao
        FROM candidaturas ca
        JOIN vagas v ON ca.vaga_id = v.id
        JOIN empresas e ON v.empresa_id = e.id
        WHERE ca.candidato_id = ?
        ORDER BY ca.posicao ASC
    ''', (session['candidato_id'],))
    
    vagas_candidatadas = cursor.fetchall()
    
    # Buscar vagas onde NÃO se candidatou
    cursor.execute('''
        SELECT v.id, v.titulo, v.descricao, v.requisitos, v.salario_oferecido, e.nome as empresa_nome
        FROM vagas v
        JOIN empresas e ON v.empresa_id = e.id
        WHERE v.id NOT IN (
            SELECT vaga_id FROM candidaturas WHERE candidato_id = ?
        )
    ''', (session['candidato_id'],))
    
    vagas_disponiveis = cursor.fetchall()
    
    cursor.execute('SELECT pretensao_salarial, texto_curriculo FROM candidatos WHERE id = ?', (session['candidato_id'],))
    candidato_info = cursor.fetchone()
    
    conn.close()
    
    # Calcular scores para vagas disponíveis
    avaliador = criar_avaliador(MODO_IA)
    vagas_com_score = []
    for vaga in vagas_disponiveis:
        score = avaliador.calcular_score(
            candidato_info[1], 
            vaga[3], 
            candidato_info[0], 
            vaga[4]
        )
        vagas_com_score.append(vaga + (score,))
    
    # Ordenar por score e pegar apenas as TOP_JOBS
    vagas_com_score.sort(key=lambda x: x[6], reverse=True)
    top_vagas = vagas_com_score[:TOP_JOBS]
    
    return render_template('dashboard_candidato.html', 
                         vagas_recomendadas=top_vagas,
                         vagas_candidatadas=vagas_candidatadas)

@app.route('/upload_curriculo', methods=['GET', 'POST'])
def upload_curriculo():
    if 'candidato_id' not in session:
        return redirect(url_for('login_candidato'))
    
    if request.method == 'POST':
        resultado = processar_upload_curriculo(request, session['candidato_id'])
        
        if resultado['sucesso']:
            return render_template('processar_curriculo.html', 
                                 dados_extraidos=resultado['dados_extraidos'],
                                 mensagens=resultado['mensagens'])
        else:
            for mensagem in resultado['mensagens']:
                flash(mensagem['texto'], mensagem['tipo'])
    
    return render_template('upload_curriculo.html')

@app.route('/finalizar_curriculo', methods=['POST'])
def finalizar_curriculo():
    if 'candidato_id' not in session:
        return redirect(url_for('login_candidato'))
    
    resultado = finalizar_processamento_curriculo(request, session['candidato_id'])
    
    for mensagem in resultado['mensagens']:
        flash(mensagem['texto'], mensagem['tipo'])
    
    if resultado['sucesso']:
        return redirect(url_for('dashboard_candidato'))
    else:
        return redirect(url_for('upload_curriculo'))

@app.route('/candidatar/<int:vaga_id>')
def candidatar(vaga_id):
    if 'candidato_id' not in session:
        return redirect(url_for('login_candidato'))
    
    from utils.helpers import processar_candidatura
    resultado = processar_candidatura(session['candidato_id'], vaga_id, MODO_IA)
    
    for mensagem in resultado['mensagens']:
        flash(mensagem['texto'], mensagem['tipo'])
    
    return redirect(url_for('dashboard_candidato'))

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
        
        cursor.execute('''
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
    
    cursor.execute('''
        SELECT nome, telefone, linkedin, pretensao_salarial, 
               experiencia, competencias, resumo_profissional
        FROM candidatos WHERE id = ?
    ''', (session['candidato_id'],))
    
    candidato = cursor.fetchone()
    conn.close()
    
    return render_template('editar_perfil_candidato.html', candidato=candidato)

@app.route('/editar_vaga/<int:vaga_id>', methods=['GET', 'POST'])
def editar_vaga(vaga_id):
    if 'empresa_id' not in session:
        return redirect(url_for('login_empresa'))
    
    conn = sqlite3.connect('recrutamento.db')
    cursor = conn.cursor()
    
    # Verificar se a vaga pertence à empresa
    cursor.execute('SELECT * FROM vagas WHERE id = ? AND empresa_id = ?', 
                   (vaga_id, session['empresa_id']))
    vaga = cursor.fetchone()
    
    if not vaga:
        flash('Vaga não encontrada', 'error')
        return redirect(url_for('dashboard_empresa'))
    
    if request.method == 'POST':
        titulo = request.form['titulo']
        descricao = request.form['descricao']
        requisitos = request.form['requisitos']
        salario_oferecido = float(request.form['salario_oferecido'])
        
        cursor.execute('''
            UPDATE vagas 
            SET titulo = ?, descricao = ?, requisitos = ?, salario_oferecido = ?
            WHERE id = ?
        ''', (titulo, descricao, requisitos, salario_oferecido, vaga_id))
        
        conn.commit()
        conn.close()
        
        flash('Vaga atualizada com sucesso!', 'success')
        return redirect(url_for('dashboard_empresa'))
    
    conn.close()
    return render_template('editar_vaga.html', vaga=vaga)

@app.route('/minhas_candidaturas')
def minhas_candidaturas():
    if 'candidato_id' not in session:
        return redirect(url_for('login_candidato'))
    
    conn = sqlite3.connect('recrutamento.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT v.id, v.titulo, e.nome as empresa_nome, v.salario_oferecido,
               ca.score, ca.posicao, ca.data_candidatura
        FROM candidaturas ca
        JOIN vagas v ON ca.vaga_id = v.id
        JOIN empresas e ON v.empresa_id = e.id
        WHERE ca.candidato_id = ?
        ORDER BY ca.data_candidatura DESC
    ''', (session['candidato_id'],))
    
    candidaturas = cursor.fetchall()
    conn.close()
    
    return render_template('minhas_candidaturas.html', candidaturas=candidaturas)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    inicializar_banco()
    app.run(host='0.0.0.0', port=5000, debug=True)
