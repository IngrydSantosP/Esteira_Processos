import os
import sqlite3
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
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


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


def processar_curriculo(texto_curriculo):
    """Processa o texto do currículo e extrai informações relevantes"""
    experiencia = ""
    competencias = ""
    resumo_profissional = ""

    # Extrair seções do currículo usando regex
    texto_upper = texto_curriculo.upper()

    # Buscar experiência profissional
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

    # Buscar competências/habilidades
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

    # Se não encontrou seções específicas, usar o texto completo como resumo
    if not experiencia and not competencias:
        resumo_profissional = texto_curriculo[:500] + "..." if len(
            texto_curriculo) > 500 else texto_curriculo

    return experiencia, competencias, resumo_profissional


def processar_upload_curriculo(request, candidato_id):
    """Processa o upload de currículo e retorna resultado"""
    resultado = {'sucesso': False, 'mensagens': [], 'dados_extraidos': None}

    try:
        if 'arquivo' not in request.files:
            resultado['mensagens'].append({
                'texto': 'Nenhum arquivo selecionado',
                'tipo': 'error'
            })
            return resultado

        arquivo = request.files['arquivo']

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
            texto_curriculo = extrair_texto_pdf(caminho_arquivo)

            if texto_curriculo:
                # Processar currículo
                experiencia, competencias, resumo_profissional = processar_curriculo(
                    texto_curriculo)

                # Salvar texto do currículo no banco
                conn = sqlite3.connect('recrutamento.db')
                cursor = conn.cursor()

                cursor.execute(
                    '''
                    UPDATE candidatos 
                    SET texto_curriculo = ?, caminho_curriculo = ?
                    WHERE id = ?
                ''', (texto_curriculo, nome_arquivo, candidato_id))

                conn.commit()
                conn.close()

                resultado['sucesso'] = True
                resultado['dados_extraidos'] = {
                    'experiencia': experiencia,
                    'competencias': competencias,
                    'resumo_profissional': resumo_profissional
                }
                resultado['mensagens'].append({
                    'texto':
                    'Currículo processado com sucesso! Revise as informações extraídas:',
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
            if 'caminho_arquivo' in locals() and os.path.exists(
                    caminho_arquivo):
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
        resumo_profissional = request.form.get('resumo_profissional',
                                               '').strip()

        # Validar se pelo menos um campo foi preenchido
        if not experiencia and not competencias and not resumo_profissional:
            resultado['mensagens'].append({
                'texto':
                'Por favor, preencha pelo menos um dos campos antes de finalizar.',
                'tipo': 'error'
            })
            return resultado

        # Salvar no banco
        conn = sqlite3.connect('recrutamento.db')
        cursor = conn.cursor()

        cursor.execute(
            '''
            UPDATE candidatos 
            SET experiencia = ?, competencias = ?, resumo_profissional = ?
            WHERE id = ?
        ''', (experiencia, competencias, resumo_profissional, candidato_id))

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

def extrair_informacoes_curriculo(caminho_pdf):
    """
    Extrai informações relevantes do currículo em PDF
    """
    try:
        # Extrair texto do PDF
        texto = extrair_texto_pdf(caminho_pdf)

        if not texto:
            return {
                'nome': '',
                'email': '',
                'telefone': '',
                'experiencias': '',
                'formacao': '',
                'habilidades': '',
                'resumo': 'Não foi possível extrair informações do currículo.'
            }

        # Usar IA para extrair informações estruturadas
        informacoes = extrair_com_ia(texto)

        # Gerar resumo automático se não existir
        if not informacoes.get('resumo') or informacoes['resumo'] == '':
            informacoes['resumo'] = gerar_resumo_automatico(texto, informacoes)

        return informacoes

    except Exception as e:
        print(f"Erro ao extrair informações do currículo: {e}")
        return {
            'nome': '',
            'email': '',
            'telefone': '',
            'experiencias': '',
            'formacao': '',
            'habilidades': '',
            'resumo': 'Erro ao processar currículo.'
        }

def gerar_resumo_automatico(texto_completo, informacoes):
    """
    Gera um resumo automático baseado nas informações extraídas
    """
    try:
        resumo_parts = []

        # Adicionar formação se disponível
        if informacoes.get('formacao'):
            resumo_parts.append(f"Formação: {informacoes['formacao'][:100]}...")

        # Adicionar experiência se disponível
        if informacoes.get('experiencias'):
            resumo_parts.append(f"Experiência: {informacoes['experiencias'][:150]}...")

        # Adicionar habilidades se disponível
        if informacoes.get('habilidades'):
            resumo_parts.append(f"Principais habilidades: {informacoes['habilidades'][:100]}...")

        # Se não tem informações suficientes, extrair do texto bruto
        if not resumo_parts:
            # Pegar primeiras 300 caracteres do texto limpo
            texto_limpo = ' '.join(texto_completo.split())
            resumo_parts.append(texto_limpo[:300] + "...")

        return ' | '.join(resumo_parts)

    except Exception as e:
        print(f"Erro ao gerar resumo automático: {e}")
        return "Resumo não disponível."