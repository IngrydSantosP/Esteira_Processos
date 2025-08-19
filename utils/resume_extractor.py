import os
from db import get_db_connection
from werkzeug.utils import secure_filename
import fitz  # PyMuPDF
import re

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf'}

# Criar pasta de uploads se não existir
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


def arquivo_permitido(filename):
    """Verifica se o arquivo tem extensão permitida"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def extrair_texto_pdf(caminho_arquivo):
    """Extrai texto de um arquivo PDF"""
    try:
        with fitz.open(caminho_arquivo) as doc:
            texto = ""
            for page in doc:
                texto += page.get_text()
        return texto
    except Exception as e:
        print(f"Erro ao extrair texto do PDF: {e}")
        return None


def processar_curriculo(texto_curriculo):
    """Processa o texto do currículo e extrai informações relevantes"""
    experiencia = ""
    competencias = ""
    resumo_profissional = ""

    texto_upper = texto_curriculo.upper()

    # Experiência profissional
    patterns_exp = [
        r'EXPERIÊNCIA PROFISSIONAL(.*?)(?=FORMAÇÃO|EDUCAÇÃO|COMPETÊNCIAS|HABILIDADES|$)',
        r'EXPERIÊNCIA(.*?)(?=FORMAÇÃO|EDUCAÇÃO|COMPETÊNCIAS|HABILIDADES|$)',
        r'HISTÓRICO PROFISSIONAL(.*?)(?=FORMAÇÃO|EDUCAÇÃO|COMPETÊNCIAS|HABILIDADES|$)'
    ]
    for pattern in patterns_exp:
        match = re.search(pattern, texto_upper, re.DOTALL)
        if match:
            experiencia = match.group(1).strip()
            break

    # Competências / habilidades
    patterns_comp = [
        r'COMPETÊNCIAS(.*?)(?=EXPERIÊNCIA|FORMAÇÃO|EDUCAÇÃO|$)',
        r'HABILIDADES(.*?)(?=EXPERIÊNCIA|FORMAÇÃO|EDUCAÇÃO|$)',
        r'CONHECIMENTOS(.*?)(?=EXPERIÊNCIA|FORMAÇÃO|EDUCAÇÃO|$)'
    ]
    for pattern in patterns_comp:
        match = re.search(pattern, texto_upper, re.DOTALL)
        if match:
            competencias = match.group(1).strip()
            break

    # Caso não encontre seções específicas
    if not experiencia and not competencias:
        resumo_profissional = texto_curriculo[:500] + "..." if len(texto_curriculo) > 500 else texto_curriculo

    return experiencia, competencias, resumo_profissional


def processar_upload_curriculo(request, candidato_id):
    """Processa o upload de currículo e retorna resultado"""
    resultado = {'sucesso': False, 'mensagens': [], 'dados_extraidos': None}

    if 'arquivo' not in request.files:
        resultado['mensagens'].append({'texto': 'Nenhum arquivo selecionado', 'tipo': 'error'})
        return resultado

    arquivo = request.files['arquivo']
    if arquivo.filename == '':
        resultado['mensagens'].append({'texto': 'Nenhum arquivo selecionado', 'tipo': 'error'})
        return resultado

    if not arquivo_permitido(arquivo.filename):
        resultado['mensagens'].append({'texto': 'Tipo de arquivo não permitido. Use apenas PDF.', 'tipo': 'error'})
        return resultado

    nome_arquivo = secure_filename(arquivo.filename)
    caminho_arquivo = os.path.join(UPLOAD_FOLDER, f"candidato_{candidato_id}_{nome_arquivo}")
    arquivo.save(caminho_arquivo)

    texto_curriculo = extrair_texto_pdf(caminho_arquivo)
    if not texto_curriculo:
        resultado['mensagens'].append({'texto': 'Erro ao extrair texto do PDF', 'tipo': 'error'})
        return resultado

    experiencia, competencias, resumo_profissional = processar_curriculo(texto_curriculo)

    # Salvar no banco
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            '''
            UPDATE candidatos 
            SET texto_curriculo = %s, caminho_curriculo = %s
            WHERE id = %s
            ''', (texto_curriculo, nome_arquivo, candidato_id)
        )
        conn.commit()
        resultado['sucesso'] = True
        resultado['dados_extraidos'] = {
            'experiencia': experiencia,
            'competencias': competencias,
            'resumo_profissional': resumo_profissional
        }
        resultado['mensagens'].append({'texto': 'Currículo processado com sucesso!', 'tipo': 'success'})
    except Exception as e:
        resultado['mensagens'].append({'texto': f'Erro ao salvar currículo: {e}', 'tipo': 'error'})
    finally:
        conn.close()

    return resultado


def finalizar_processamento_curriculo(request, candidato_id):
    """Finaliza o processamento do currículo salvando as informações editadas"""
    resultado = {'sucesso': False, 'mensagens': []}
    experiencia = request.form.get('experiencia', '').strip()
    competencias = request.form.get('competencias', '').strip()
    resumo_profissional = request.form.get('resumo_profissional', '').strip()

    if not experiencia and not competencias and not resumo_profissional:
        resultado['mensagens'].append({'texto': 'Preencha pelo menos um campo antes de finalizar.', 'tipo': 'error'})
        return resultado

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            '''
            UPDATE candidatos 
            SET experiencia = %s, competencias = %s, resumo_profissional = %s
            WHERE id = %s
            ''', (experiencia, competencias, resumo_profissional, candidato_id)
        )
        conn.commit()
        resultado['sucesso'] = True
        resultado['mensagens'].append({'texto': 'Currículo processado e salvo com sucesso!', 'tipo': 'success'})
    except Exception as e:
        resultado['mensagens'].append({'texto': f'Erro ao salvar informações: {e}', 'tipo': 'error'})
    finally:
        conn.close()

    return resultado


def gerar_resumo_automatico(texto_completo, informacoes):
    """Gera um resumo automático baseado nas informações extraídas"""
    try:
        resumo_parts = []
        if informacoes.get('formacao'):
            resumo_parts.append(f"Formação: {informacoes['formacao'][:100]}...")
        if informacoes.get('experiencias'):
            resumo_parts.append(f"Experiência: {informacoes['experiencias'][:150]}...")
        if informacoes.get('habilidades'):
            resumo_parts.append(f"Principais habilidades: {informacoes['habilidades'][:100]}...")

        if not resumo_parts:
            texto_limpo = ' '.join(texto_completo.split())
            resumo_parts.append(texto_limpo[:300] + "...")

        return ' | '.join(resumo_parts)
    except Exception as e:
        print(f"Erro ao gerar resumo automático: {e}")
        return "Resumo não disponível."
