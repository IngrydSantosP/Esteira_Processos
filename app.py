from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from utils.helpers import inicializar_banco
from avaliador import get_avaliador as criar_avaliador
from dotenv import load_dotenv
from datetime import datetime, timedelta
from utils.notifications import (notification_system)
from utils.ia_assistant import IAAssistant
from scheduler import iniciar_scheduler_background
from functools import lru_cache
from datetime import datetime, timedelta, timezone
import os

from db import get_db_connection
from config import get_config
from routes.auth import auth_bp
from routes.vagas import vagas_bp
from routes.relatorios import relatorios_bp
from routes.candidaturas import candidaturas_bp
from routes.ia_api import ia_api_bp
from routes.favoritos import favoritos_bp
from routes.notifications_routes import notifications_bp
from routes.score_personalizado import score_bp
from routes.filtro import filtro_bp
from werkzeug.utils import secure_filename
from routes.arquivos import arquivos_bp, upload_curriculo
data_brasil = (datetime.now(timezone.utc) -
               timedelta(hours=3)).strftime('%d-%m-%y %H:%M:%S')

load_dotenv()

app = Flask(__name__)

# Registrar blueprint
app.register_blueprint(auth_bp)
app.register_blueprint(vagas_bp)
app.register_blueprint(relatorios_bp)
app.register_blueprint(candidaturas_bp)
app.register_blueprint(ia_api_bp)
app.register_blueprint(favoritos_bp)
app.register_blueprint(notifications_bp)
app.register_blueprint(score_bp)
app.register_blueprint(filtro_bp)
app.register_blueprint(arquivos_bp)


# Inicializar banco de dados
inicializar_banco()
# Iniciar scheduler em background
iniciar_scheduler_background()

# Carregar configuração
config = get_config()
print("Configuração carregada:", config)



for rule in app.url_map.iter_rules():
    print(rule.endpoint, rule)


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

# Renamed function to avoid confusion with the corrected import
def get_avaliador_cached(modo='local'):
    """Cache de avaliadores para evitar recriar objetos"""
    if modo not in _avaliadores_cache:
        # Ensure this function call matches the actual function name in avaliador.py
        from avaliador import get_avaliador as criar_avaliador_impl
        _avaliadores_cache[modo] = criar_avaliador_impl(modo)
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



@app.context_processor
def inject_user_data():
    imagem_perfil = None
    nome_usuario = None

    if "tipo_usuario" in session:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        if session["tipo_usuario"] == "candidato" and "candidato_id" in session:
            cursor.execute("SELECT nome, imagem_perfil FROM candidatos WHERE id = %s", (session["candidato_id"],))
            usuario = cursor.fetchone()
            if usuario:
                imagem_perfil = usuario["imagem_perfil"]
                nome_usuario = usuario["nome"]

        elif session["tipo_usuario"] == "empresa" and "empresa_id" in session:
            cursor.execute("SELECT nome, imagem_perfil FROM empresas WHERE id = %s", (session["empresa_id"],))
            usuario = cursor.fetchone()
            if usuario:
                imagem_perfil = usuario["imagem_perfil"]
                nome_usuario = usuario["nome"]

        conn.close()

    return dict(imagem_perfil=imagem_perfil, nome_usuario=nome_usuario)




@app.route('/upload-curriculo', methods=['GET', 'POST'])
def upload_curriculo_route():
    if 'candidato_id' not in session:
        flash('Faça login para acessar esta página.', 'error')
        return redirect(url_for('auth.login_candidato'))

    if request.method == 'POST':
        if 'curriculo' not in request.files:
            flash('Nenhum arquivo enviado.', 'error')
            return redirect(request.url)

        arquivo = request.files['curriculo']
        if arquivo.filename == '':
            flash('Nome do arquivo vazio.', 'error')
            return redirect(request.url)

        if not arquivo.filename.lower().endswith('.pdf'):
            flash('Apenas arquivos PDF são permitidos.', 'error')
            return redirect(request.url)

        nome_usuario = f"curriculo_{session['candidato_id']}_{secure_filename(arquivo.filename)}"
        resultado = upload_curriculo(arquivo, nome_usuario)

        if resultado['sucesso']:
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO curriculos (candidato_id, url, public_id, tipo_arquivo, tamanho_bytes)
                    VALUES (%s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE url=VALUES(url), public_id=VALUES(public_id), tipo_arquivo=VALUES(tipo_arquivo), tamanho_bytes=VALUES(tamanho_bytes);
                """, (
                    session['candidato_id'],
                    resultado['url'],
                    resultado['public_id'],
                    resultado.get('tipo'),
                    resultado.get('tamanho_bytes')
                ))
                conn.commit()
                flash('Currículo enviado com sucesso!', 'success')
                return redirect(url_for('candidaturas.dashboard_candidato'))
            except Exception as e:
                flash(f'Erro ao salvar no banco de dados: {e}', 'error')
            finally:
                if conn:
                    conn.close()
        else:
            flash(f"Erro no upload: {resultado['erro']}", 'error')

    return render_template('candidato/upload_curriculo.html')









@app.route('/api/todas-vagas')
def api_todas_vagas():
    """API para buscar todas as vagas disponíveis"""
    if 'candidato_id' not in session:
        return jsonify({'error': 'Não autorizado'}), 401

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Buscar todas as vagas ativas
        query = '''
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
            ORDER BY v.data_criacao DESC
            LIMIT 50
        '''

        cursor.execute(query, [session['candidato_id'], session['candidato_id']])
        vagas_raw = cursor.fetchall()

        # Buscar informações do candidato para calcular scores
        cursor.execute(
            'SELECT pretensao_salarial, resumo_profissional, endereco FROM candidatos WHERE id = %s',
            (session['candidato_id'], ))
        candidato_info = cursor.fetchone()

        if not candidato_info:
            return jsonify({'error': 'Candidato não encontrado'}), 404

        # Calcular scores
        config = get_config()
        avaliador = get_avaliador_cached(config['MODO_IA']) # Updated call
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
                'urgencia': vaga[11],
                'localizacao': f"{vaga[12]}, {vaga[13]}" if vaga[12] and vaga[13] else vaga[12] or '',
                'categoria': vaga[14],
                'score': float(score)
            }
            vagas_processadas.append(vaga_processada)

        # Ordenar por score
        vagas_processadas.sort(key=lambda x: x['score'], reverse=True)

        return jsonify(vagas_processadas)

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()


@app.route('/api/buscar-vagas')
def api_buscar_vagas():
    """API para busca avançada de vagas com filters"""
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

        # Adicionar filters
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
            'SELECT pretensao_salarial, resumo_profissional, endereco FROM candidatos WHERE id = %s',
            (session['candidato_id'], ))
        candidato_info = cursor.fetchone()

        if not candidato_info:
            return jsonify({'error': 'Candidato não encontrado'}), 404

        # Calcular scores
        config = get_config()
        avaliador = get_avaliador_cached(config['MODO_IA']) # Updated call
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


#modal encerramento com problema
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

    conn = get_db_connection()
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
                    conn_email = get_db_connection()
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
                    conn_email = get_db_connection()
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


@app.route("/candidaturas/api/json/candidatos_vaga/<int:vaga_id>")
def api_candidatos_vaga(vaga_id):
    if 'empresa_id' not in session:
        return jsonify({'error': 'Não autorizado'}), 401

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Verificar se a vaga pertence à empresa
        cursor.execute('SELECT 1 FROM vagas WHERE id = %s AND empresa_id = %s',
                       (vaga_id, session['empresa_id']))
        if not cursor.fetchone():
            return jsonify({'error': 'Vaga não encontrada'}), 404

        # Buscar dados mínimos dos candidatos
        cursor.execute('''
            SELECT c.id, c.nome, ca.score
            FROM candidaturas ca
            JOIN candidatos c ON ca.candidato_id = c.id
            WHERE ca.vaga_id = %s
            ORDER BY ca.score DESC
        ''', (vaga_id, ))

        candidatos = [{
            'id': c[0],
            'nome': c[1],
            'score': float(c[2])
        } for c in cursor.fetchall()]

        return jsonify(candidatos)

    except Exception as e:
        print(f"Erro ao retornar candidatos JSON da vaga {vaga_id}: {e}")
        return jsonify({'error': 'Erro ao carregar candidatos'}), 500
    finally:
        conn.close()



@app.route('/politica-privacidade')
def politica_privacidade():
    from datetime import datetime
    return render_template('politica_privacidade.html',
                           data_atual=datetime.now().strftime('%B de %Y'))


@app.route('/logout')
def logout():
    session.clear()
    flash('Logout realizado com sucesso!', 'success')
    return redirect(url_for('vagas.index'))


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000, use_reloader=False)