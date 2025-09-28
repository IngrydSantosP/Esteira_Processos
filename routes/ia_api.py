from flask import Blueprint, jsonify, session
from db import get_db_connection
from ia_utils import get_ia_assistant
from utils.notifications import notification_system
import mysql.connector
from collections import Counter

ia_api_bp = Blueprint("ia_api", __name__)

@ia_api_bp.route("/api/ia/analisar-curriculo")
def api_analisar_curriculo():
    """API para análise de currículo do candidato logado"""
    if "candidato_id" not in session:
        return jsonify({"error": "Não autorizado"}), 401

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        candidato_id = session["candidato_id"]
        
        cursor.execute("SELECT resumo_profissional, nome, competencias FROM candidatos WHERE id = %s",
                       (candidato_id,))
        resultado = cursor.fetchone()

        if not resultado or not resultado[0]:
            return jsonify({"error": "Currículo não encontrado"}), 404

        curriculo_texto, nome, competencias = resultado

        # Análise básica do currículo
        analise = {
            "score_geral": 75,
            "nivel_senioridade": "Pleno",
            "tecnologias_identificadas": [
                {"nome": "Python"}, 
                {"nome": "JavaScript"}, 
                {"nome": "SQL"}
            ],
            "pontos_fortes": [
                "Experiência diversificada",
                "Conhecimento técnico sólido",
                "Perfil profissional bem estruturado"
            ],
            "areas_melhoria": [
                "Adicionar mais certificações",
                "Incluir projetos práticos",
                "Detalhar métricas de resultados"
            ]
        }

        return jsonify(analise)

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@ia_api_bp.route("/api/ia/analise-curriculo/<int:candidato_id>")
def api_analise_curriculo(candidato_id):
    """API para análise de currículo com IA"""
    if "candidato_id" not in session:
        return jsonify({"error": "Não autorizado"}), 401

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Verificar se o candidato logado é o mesmo que está sendo analisado
        if candidato_id != session["candidato_id"]:
            return jsonify({"error": "Acesso negado para este currículo"}), 403

        cursor.execute("SELECT resumo_profissional FROM candidatos WHERE id = ?",
                       (candidato_id, ))
        resultado = cursor.fetchone()

        if not resultado or not resultado[0]:
            return jsonify({"error": "Currículo não encontrado"}), 404

        curriculo_texto = resultado[0]

        # Analisar currículo com IA
        analise = get_ia_assistant().analisar_curriculo(candidato_id,
                                                         curriculo_texto)

        return jsonify(analise)

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@ia_api_bp.route("/api/ia/recomendacoes-vagas")
def api_recomendacoes_ia():
    """API para recomendações personalizadas de vagas"""
    if "candidato_id" not in session:
        return jsonify({"error": "Não autorizado"}), 401

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        candidato_id = session["candidato_id"]

        # Buscar currículo do candidato
        cursor.execute("SELECT resumo_profissional FROM candidatos WHERE id = ?",
                       (candidato_id, ))
        resultado = cursor.fetchone()

        if not resultado or not resultado[0]:
            return jsonify({"error": "Currículo não encontrado"}), 404

        curriculo_texto = resultado[0]

        # Obter recomendações da IA
        recomendacoes = get_ia_assistant().recomendar_vagas_personalizadas(
            candidato_id, curriculo_texto)

        return jsonify(recomendacoes)

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@ia_api_bp.route("/api/ia/dicas-vaga/<int:vaga_id>")
def api_dicas_vaga_ia(vaga_id):
    """API para dicas específicas de uma vaga"""
    if "candidato_id" not in session:
        return jsonify({"error": "Não autorizado"}), 401

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        candidato_id = session["candidato_id"]

        # Buscar dados do candidato e da vaga
        cursor.execute(
            """
            SELECT c.resumo_profissional, v.requisitos, v.salario_oferecido
            FROM candidatos c, vagas v
            WHERE c.id = ? AND v.id = ? AND v.status = 'Ativa'
        """, (candidato_id, vaga_id))

        resultado = cursor.fetchone()

        if not resultado:
            return jsonify({"error": "Dados não encontrados"}), 404

        curriculo_texto, requisitos_vaga, salario_vaga = resultado

        # Gerar dicas da IA
        dicas = get_ia_assistant().gerar_dicas_melhoria_vaga(curriculo_texto,
                                                       requisitos_vaga,
                                                       salario_vaga)

        return jsonify(dicas)

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@ia_api_bp.route("/api/ia/enviar-recomendacoes", methods=["POST"])
def api_enviar_recomendacoes_email():
    """API para enviar recomendações por email"""
    if "candidato_id" not in session:
        return jsonify({"error": "Não autorizado"}), 401

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        candidato_id = session["candidato_id"]

        # Buscar dados do candidato
        cursor.execute(
            "SELECT nome, email, resumo_profissional FROM candidatos WHERE id = ?",
            (candidato_id, ))
        resultado = cursor.fetchone()

        if not resultado:
            return jsonify({"error": "Candidato não encontrado"}), 404

        candidato_nome, candidato_email, curriculo_texto = resultado

        # Obter análise e recomendações
        analise = get_ia_assistant().analisar_curriculo(candidato_id,
                                                         curriculo_texto)
        recomendacoes = get_ia_assistant().recomendar_vagas_personalizadas(
            candidato_id, curriculo_texto)

        # Gerar dicas gerais
        dicas = []
        if analise["areas_melhoria"]:
            for area in analise["areas_melhoria"][:3]:
                dicas.append({
                    "titulo": f"Melhore: {area}",
                    "descricao":
                    f"Considere desenvolver mais esta área do seu perfil",
                    "prioridade": "media",
                    "icone": "💡"
                })

        # Dados para o template
        template_data = {
            "candidato_nome": candidato_nome,
            "analise": analise,
            "recomendacoes": recomendacoes,
            "dicas": dicas
        }

        # Enviar email com template da IA
        assunto = "🤖 Recomendações Personalizadas da IA"
        sucesso = notification_system.enviar_email(
            candidato_email, assunto,
            "Suas recomendações personalizadas estão prontas!", template_data,
            "recomendacao_ia")

        if sucesso:
            return jsonify({
                "success": True,
                "message": "Recomendações enviadas por email!"
            })
        else:
            return jsonify({
                "success": False,
                "message": "Erro ao enviar email"
            }), 500

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@ia_api_bp.route('/api/dicas-favoritas')
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
