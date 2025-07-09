
import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from utils.helpers import inicializar_banco
from utils.resume_extractor import processar_upload_curriculo, finalizar_processamento_curriculo
from avaliador import criar_avaliador
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from flask import send_file
import io

app = Flask(__name__)
app.secret_key = 'chave-secreta-mvp-recrutamento'

# Configurações do ambiente
MODO_IA = os.getenv('MODO_IA', 'local')
TOP_JOBS = int(os.getenv('TOP_JOBS', '3'))

def gerar_feedback_ia_vaga(total, alta_compatibilidade, media_compatibilidade, baixa_compatibilidade):
    """Gera feedback inteligente sobre os candidatos da vaga"""
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
                'texto': f'{alta_compatibilidade} candidato(s) com perfil excelente (80%+)',
                'cor': 'text-green-600',
                'icone': '🎯'
            }
        else:
            return {
                'texto': f'{alta_compatibilidade} candidato(s) muito compatível(eis)',
                'cor': 'text-green-500',
                'icone': '✅'
            }
    
    if media_compatibilidade > 0:
        return {
            'texto': f'{media_compatibilidade} candidato(s) com bom potencial (60-79%)',
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
    
    # Buscar vagas com estatísticas de candidatos
    cursor.execute('''
        SELECT v.*, 
               COUNT(ca.id) as total_candidatos,
               COUNT(CASE WHEN ca.score >= 80 THEN 1 END) as candidatos_80_plus,
               COUNT(CASE WHEN ca.score >= 60 AND ca.score < 80 THEN 1 END) as candidatos_60_79,
               COUNT(CASE WHEN ca.score < 60 THEN 1 END) as candidatos_abaixo_60
        FROM vagas v
        LEFT JOIN candidaturas ca ON v.id = ca.vaga_id
        WHERE v.empresa_id = ?
        GROUP BY v.id, v.empresa_id, v.titulo, v.descricao, v.requisitos, v.salario_oferecido, v.data_criacao
        ORDER BY v.data_criacao DESC
    ''', (session['empresa_id'],))
    
    vagas_com_stats = cursor.fetchall()
    conn.close()
    
    # Gerar feedback de IA para cada vaga
    vagas_processadas = []
    for vaga in vagas_com_stats:
        vaga_dict = {
            'id': vaga[0],
            'empresa_id': vaga[1], 
            'titulo': vaga[2],
            'descricao': vaga[3],
            'requisitos': vaga[4],
            'salario_oferecido': vaga[5],
            'data_criacao': vaga[6],
            'total_candidatos': vaga[7],
            'candidatos_80_plus': vaga[8],
            'candidatos_60_79': vaga[9],
            'candidatos_abaixo_60': vaga[10],
            'feedback_ia': gerar_feedback_ia_vaga(vaga[7], vaga[8], vaga[9], vaga[10])
        }
        vagas_processadas.append(vaga_dict)
    
    return render_template('dashboard_empresa.html', vagas=vagas_processadas)

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
        SELECT c.nome, c.email, c.telefone, c.linkedin, ca.score, ca.posicao, c.id
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
        
        # Exibir todas as mensagens como flash
        for mensagem in resultado['mensagens']:
            flash(mensagem['texto'], mensagem['tipo'])
        
        if resultado['sucesso']:
            return render_template('processar_curriculo.html', 
                                 dados_extraidos=resultado['dados_extraidos'])
        else:
            return redirect(request.url)
    
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

@app.route('/baixar_curriculo/<int:candidato_id>')
def baixar_curriculo(candidato_id):
    if 'empresa_id' not in session:
        return redirect(url_for('login_empresa'))
    
    conn = sqlite3.connect('recrutamento.db')
    cursor = conn.cursor()
    
    # Verificar se a empresa tem acesso ao candidato (através de candidatura)
    cursor.execute('''
        SELECT COUNT(*) FROM candidaturas ca
        JOIN vagas v ON ca.vaga_id = v.id
        WHERE ca.candidato_id = ? AND v.empresa_id = ?
    ''', (candidato_id, session['empresa_id']))
    
    if cursor.fetchone()[0] == 0:
        flash('Acesso negado ao currículo', 'error')
        return redirect(url_for('dashboard_empresa'))
    
    # Buscar dados do candidato
    cursor.execute('''
        SELECT nome, caminho_curriculo
        FROM candidatos WHERE id = ?
    ''', (candidato_id,))
    
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
    
    return send_file(
        caminho_curriculo,
        as_attachment=True,
        download_name=nome_download,
        mimetype='application/pdf'
    )

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    inicializar_banco()
    app.run(host='0.0.0.0', port=5000, debug=True)
