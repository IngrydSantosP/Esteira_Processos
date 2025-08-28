import os
import mysql.connector
from mysql.connector import Error
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
        doc = fitz.open(caminho_arquivo)
        texto = ""
        for page in doc:
            texto += page.get_text()
        doc.close()
        return texto
    except Exception as e:
        print(f"Erro ao extrair texto do PDF: {e}")
        return None


def processar_curriculo(texto_completo):
    """
    Processa o texto bruto do currículo e extrai informações relevantes:
    experiência, competências, resumo profissional e formação.
    """
    experiencia = ""
    competencias = ""
    resumo_profissional = ""
    formacao = ""

    texto_upper = texto_completo.upper()

    # Extrair resumo profissional ou "sobre mim"
    patterns_resumo = [
        r'SOBRE MIM(.*?)(?=EXPERIÊNCIA|FORMAÇÃO|COMPETÊNCIAS|HABILIDADES|EDUCAÇÃO|$)',
        r'RESUMO PROFISSIONAL(.*?)(?=EXPERIÊNCIA|FORMAÇÃO|COMPETÊNCIAS|HABILIDADES|EDUCAÇÃO|$)',
        r'PERFIL PROFISSIONAL(.*?)(?=EXPERIÊNCIA|FORMAÇÃO|COMPETÊNCIAS|HABILIDADES|EDUCAÇÃO|$)'
    ]
    for pattern in patterns_resumo:
        match = re.search(pattern, texto_upper, re.DOTALL)
        if match:
            resumo_profissional = match.group(1).strip()
            break

    # Extrair experiência profissional
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

    # Extrair competências/habilidades
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

    # Extrair formação/educação
    patterns_form = [
        r'FORMAÇÃO(.*?)(?=EXPERIÊNCIA|COMPETÊNCIAS|HABILIDADES|EDUCAÇÃO|$)',
        r'EDUCAÇÃO(.*?)(?=EXPERIÊNCIA|COMPETÊNCIAS|HABILIDADES|FORMAÇÃO|$)'
    ]
    for pattern in patterns_form:
        match = re.search(pattern, texto_upper, re.DOTALL)
        if match:
            formacao = match.group(1).strip()
            break

    # Gerar resumo automaticamente caso "sobre mim" não seja encontrado
    if not resumo_profissional:
        resumo_parts = []

        if experiencia:
            resumo_parts.append(f"Possui experiência relevante na área, incluindo: {experiencia[:150].strip()}...")
        if competencias:
            resumo_parts.append(f"Demonstra competências como: {competencias[:150].strip()}...")
        if formacao:
            resumo_parts.append(f"Formação acadêmica inclui: {formacao[:150].strip()}...")

        if resumo_parts:
            resumo_profissional = " ".join(resumo_parts)
        else:
            resumo_profissional = texto_completo[:500] + "..." if len(texto_completo) > 500 else texto_completo

    return experiencia, competencias, resumo_profissional, formacao

def processar_upload_curriculo(request, candidato_id):
    """Processa o upload de currículo e retorna resultado"""
    resultado = {'sucesso': False, 'mensagens': [], 'dados_extraidos': None}

    try:
        if 'curriculo' not in request.files:
            resultado['mensagens'].append({
                'texto': 'Nenhum arquivo selecionado',
                'tipo': 'error'
            })
            return resultado

        arquivo = request.files['curriculo']

        if arquivo.filename == '':
            resultado['mensagens'].append({
                'texto': 'Nenhum arquivo selecionado',
                'tipo': 'error'
            })
            return resultado

        if arquivo and arquivo_permitido(arquivo.filename):
            nome_arquivo = secure_filename(arquivo.filename)
            caminho_arquivo = os.path.join(
                UPLOAD_FOLDER, f"candidato_{candidato_id}_{nome_arquivo}")
            arquivo.save(caminho_arquivo)

            # Extrair texto do PDF
            texto_pdf = extrair_texto_pdf(caminho_arquivo)

            if texto_pdf:
                # Processar texto do currículo para extrair dados
                experiencia, competencias, resumo_profissional, formacao = processar_curriculo(texto_pdf)

                # Salvar caminho do arquivo e dados extraídos no banco
                conn = get_db_connection()
                cursor = conn.cursor()

                cursor.execute(
                    '''
                    UPDATE candidatos 
                    SET caminho_curriculo = %s, experiencia = %s, competencias = %s, resumo_profissional = %s, formacao = %s 
                    WHERE id = %s
                    ''',
                    (nome_arquivo, experiencia, competencias, resumo_profissional, formacao, candidato_id)
                )

                conn.commit()
                conn.close()

                resultado['sucesso'] = True
                resultado['dados_extraidos'] = {
                    'experiencia': experiencia,
                    'competencias': competencias,
                    'resumo_profissional': resumo_profissional,
                    'formacao': formacao
                }
                resultado['mensagens'].append({
                    'texto': 'Currículo processado com sucesso! Revise as informações extraídas:',
                    'tipo': 'success'
                })
            else:
                resultado['mensagens'].append({
                    'texto': 'Erro ao extrair texto do arquivo PDF',
                    'tipo': 'error'
                })
        else:
            resultado['mensagens'].append({
                'texto': 'Tipo de arquivo não permitido. Use apenas PDF.',
                'tipo': 'error'
            })

    except Exception as e:
        resultado['mensagens'].append({
            'texto': f'Erro ao processar arquivo: {str(e)}',
            'tipo': 'error'
        })

        # Tentar remover arquivo em caso de erro
        try:
            if 'caminho_arquivo' in locals() and os.path.exists(caminho_arquivo):
                os.remove(caminho_arquivo)
        except:
            pass

    return resultado


def finalizar_processamento_curriculo(request, candidato_id):
    """Finaliza o processamento do currículo salvando as informações editadas"""
    resultado = {'sucesso': False, 'mensagens': []}

    try:
        experiencia = request.form.get('experiencia', '').strip()
        competencias = request.form.get('competencias', '').strip()
        resumo_profissional = request.form.get('resumo_profissional', '').strip()
        formacao = request.form.get('formacao', '').strip()

        if not experiencia and not competencias and not resumo_profissional and not formacao:
            resultado['mensagens'].append({
                'texto': 'Por favor, preencha pelo menos um dos campos antes de finalizar.',
                'tipo': 'error'
            })
            return resultado

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            '''
            UPDATE candidatos 
            SET experiencia = %s, competencias = %s, resumo_profissional = %s, formacao = %s 
            WHERE id = %s
            ''',
            (experiencia, competencias, resumo_profissional, formacao, candidato_id)
        )

        conn.commit()
        conn.close()

        resultado['sucesso'] = True
        resultado['mensagens'].append({
            'texto': 'Currículo processado e salvo com sucesso!',
            'tipo': 'success'
        })

    except Exception as e:
        resultado['mensagens'].append({
            'texto': f'Erro ao salvar informações: {str(e)}',
            'tipo': 'error'
        })

    return resultado
