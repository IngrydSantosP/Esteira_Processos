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
    experiência, competências, resumo profissional, formação, certificações,
    idiomas, disponibilidade e benefícios desejados.
    """
    experiencia = ""
    competencias = ""
    resumo_profissional = ""
    formacao = ""
    certificacoes = ""
    idiomas = ""
    disponibilidade = ""
    beneficios_desejados = ""

    texto_upper = texto_completo.upper()
    texto_original = texto_completo

    # Extrair resumo profissional ou "sobre mim"
    patterns_resumo = [
        r'SOBRE MIM(.*?)(?=EXPERIÊNCIA|FORMAÇÃO|COMPETÊNCIAS|HABILIDADES|EDUCAÇÃO|CERTIFICAÇÕES|IDIOMAS|$)',
        r'RESUMO PROFISSIONAL(.*?)(?=EXPERIÊNCIA|FORMAÇÃO|COMPETÊNCIAS|HABILIDADES|EDUCAÇÃO|CERTIFICAÇÕES|IDIOMAS|$)',
        r'PERFIL PROFISSIONAL(.*?)(?=EXPERIÊNCIA|FORMAÇÃO|COMPETÊNCIAS|HABILIDADES|EDUCAÇÃO|CERTIFICAÇÕES|IDIOMAS|$)',
        r'OBJETIVO(.*?)(?=EXPERIÊNCIA|FORMAÇÃO|COMPETÊNCIAS|HABILIDADES|EDUCAÇÃO|CERTIFICAÇÕES|IDIOMAS|$)'
    ]
    for pattern in patterns_resumo:
        match = re.search(pattern, texto_upper, re.DOTALL)
        if match:
            resumo_profissional = match.group(1).strip()
            break

    # Extrair experiência profissional
    patterns_exp = [
        r'EXPERIÊNCIA PROFISSIONAL(.*?)(?=FORMAÇÃO|EDUCAÇÃO|COMPETÊNCIAS|HABILIDADES|CERTIFICAÇÕES|IDIOMAS|$)',
        r'EXPERIÊNCIA(.*?)(?=FORMAÇÃO|EDUCAÇÃO|COMPETÊNCIAS|HABILIDADES|CERTIFICAÇÕES|IDIOMAS|$)',
        r'HISTÓRICO PROFISSIONAL(.*?)(?=FORMAÇÃO|EDUCAÇÃO|COMPETÊNCIAS|HABILIDADES|CERTIFICAÇÕES|IDIOMAS|$)',
        r'TRAJETÓRIA PROFISSIONAL(.*?)(?=FORMAÇÃO|EDUCAÇÃO|COMPETÊNCIAS|HABILIDADES|CERTIFICAÇÕES|IDIOMAS|$)'
    ]
    for pattern in patterns_exp:
        match = re.search(pattern, texto_upper, re.DOTALL)
        if match:
            experiencia = match.group(1).strip()
            break

    # Extrair competências/habilidades
    patterns_comp = [
        r'COMPETÊNCIAS(.*?)(?=EXPERIÊNCIA|FORMAÇÃO|EDUCAÇÃO|CERTIFICAÇÕES|IDIOMAS|$)',
        r'HABILIDADES(.*?)(?=EXPERIÊNCIA|FORMAÇÃO|EDUCAÇÃO|CERTIFICAÇÕES|IDIOMAS|$)',
        r'CONHECIMENTOS(.*?)(?=EXPERIÊNCIA|FORMAÇÃO|EDUCAÇÃO|CERTIFICAÇÕES|IDIOMAS|$)',
        r'SKILLS(.*?)(?=EXPERIÊNCIA|FORMAÇÃO|EDUCAÇÃO|CERTIFICAÇÕES|IDIOMAS|$)'
    ]
    for pattern in patterns_comp:
        match = re.search(pattern, texto_upper, re.DOTALL)
        if match:
            competencias = match.group(1).strip()
            break

    # Extrair formação/educação
    patterns_form = [
        r'FORMAÇÃO(.*?)(?=EXPERIÊNCIA|COMPETÊNCIAS|HABILIDADES|CERTIFICAÇÕES|IDIOMAS|$)',
        r'EDUCAÇÃO(.*?)(?=EXPERIÊNCIA|COMPETÊNCIAS|HABILIDADES|CERTIFICAÇÕES|IDIOMAS|$)',
        r'FORMAÇÃO ACADÊMICA(.*?)(?=EXPERIÊNCIA|COMPETÊNCIAS|HABILIDADES|CERTIFICAÇÕES|IDIOMAS|$)',
        r'ESCOLARIDADE(.*?)(?=EXPERIÊNCIA|COMPETÊNCIAS|HABILIDADES|CERTIFICAÇÕES|IDIOMAS|$)'
    ]
    for pattern in patterns_form:
        match = re.search(pattern, texto_upper, re.DOTALL)
        if match:
            formacao = match.group(1).strip()
            break

    # Extrair certificações
    patterns_cert = [
        r'CERTIFICAÇÕES(.*?)(?=EXPERIÊNCIA|FORMAÇÃO|COMPETÊNCIAS|HABILIDADES|IDIOMAS|$)',
        r'CERTIFICADOS(.*?)(?=EXPERIÊNCIA|FORMAÇÃO|COMPETÊNCIAS|HABILIDADES|IDIOMAS|$)',
        r'CURSOS(.*?)(?=EXPERIÊNCIA|FORMAÇÃO|COMPETÊNCIAS|HABILIDADES|IDIOMAS|$)',
        r'QUALIFICAÇÕES(.*?)(?=EXPERIÊNCIA|FORMAÇÃO|COMPETÊNCIAS|HABILIDADES|IDIOMAS|$)'
    ]
    for pattern in patterns_cert:
        match = re.search(pattern, texto_upper, re.DOTALL)
        if match:
            certificacoes = match.group(1).strip()
            break

    # Extrair idiomas
    patterns_idiomas = [
        r'IDIOMAS(.*?)(?=EXPERIÊNCIA|FORMAÇÃO|COMPETÊNCIAS|HABILIDADES|CERTIFICAÇÕES|$)',
        r'LÍNGUAS(.*?)(?=EXPERIÊNCIA|FORMAÇÃO|COMPETÊNCIAS|HABILIDADES|CERTIFICAÇÕES|$)',
        r'LANGUAGES(.*?)(?=EXPERIÊNCIA|FORMAÇÃO|COMPETÊNCIAS|HABILIDADES|CERTIFICAÇÕES|$)'
    ]
    for pattern in patterns_idiomas:
        match = re.search(pattern, texto_upper, re.DOTALL)
        if match:
            idiomas = match.group(1).strip()
            break

    # Detectar disponibilidade e modalidade preferida
    if re.search(r'REMOTO|HOME OFFICE|TRABALHO REMOTO|FREELANCER', texto_upper):
        if 'PRESENCIAL' in texto_upper or 'HÍBRIDO' in texto_upper:
            disponibilidade = "Híbrido"
        else:
            disponibilidade = "Remoto"
    elif re.search(r'PRESENCIAL', texto_upper):
        disponibilidade = "Presencial"
    else:
        disponibilidade = "Não especificado"

    # Detectar benefícios desejados comuns
    beneficios_encontrados = []
    if re.search(r'VALE[- ]REFEIÇÃO|VR|ALIMENTAÇÃO', texto_upper):
        beneficios_encontrados.append("Vale Refeição")
    if re.search(r'VALE[- ]TRANSPORTE|VT', texto_upper):
        beneficios_encontrados.append("Vale Transporte")
    if re.search(r'PLANO[- ]DE[- ]SAÚDE|CONVÊNIO[- ]MÉDICO', texto_upper):
        beneficios_encontrados.append("Plano de Saúde")
    if re.search(r'PLANO[- ]ODONTOLÓGICO|CONVÊNIO[- ]ODONTOLÓGICO', texto_upper):
        beneficios_encontrados.append("Plano Odontológico")
    if re.search(r'GYMPASS|ACADEMIA', texto_upper):
        beneficios_encontrados.append("Auxílio Academia")
    if re.search(r'FLEXIBILIDADE[- ]DE[- ]HORÁRIO|HORÁRIO[- ]FLEXÍVEL', texto_upper):
        beneficios_encontrados.append("Horário Flexível")

    beneficios_desejados = ", ".join(beneficios_encontrados) if beneficios_encontrados else ""

    # Melhorar detecção automática de informações se não encontrar seções específicas
    if not competencias:
        # Buscar por tecnologias e habilidades técnicas comuns
        tecnologias = []
        tech_patterns = [
            r'\b(PYTHON|JAVA|JAVASCRIPT|PHP|C\+\+|C#|REACT|ANGULAR|VUE|NODE\.?JS|SQL|MYSQL|POSTGRESQL|MONGODB|AWS|AZURE|DOCKER|KUBERNETES|GIT|LINUX|WINDOWS)\b'
        ]
        for pattern in tech_patterns:
            matches = re.findall(pattern, texto_upper)
            tecnologias.extend(matches)

        if tecnologias:
            competencias = "Tecnologias identificadas: " + ", ".join(set(tecnologias))

    if not idiomas:
        # Detectar idiomas comuns
        idiomas_detectados = []
        if re.search(r'\b(INGLÊS|ENGLISH|FLUENTE|INTERMEDIATE|AVANÇADO)\b', texto_upper):
            idiomas_detectados.append("Inglês")
        if re.search(r'\b(ESPANHOL|SPANISH)\b', texto_upper):
            idiomas_detectados.append("Espanhol")
        if re.search(r'\b(FRANCÊS|FRENCH)\b', texto_upper):
            idiomas_detectados.append("Francês")

        if idiomas_detectados:
            idiomas = ", ".join(idiomas_detectados)

    # Gerar resumo automaticamente caso "sobre mim" não seja encontrado
    if not resumo_profissional:
        resumo_parts = []

        if experiencia:
            resumo_parts.append(f"Possui experiência relevante na área, incluindo: {experiencia[:150].strip()}...")
        if competencias:
            resumo_parts.append(f"Demonstra competências como: {competencias[:150].strip()}...")
        if formacao:
            resumo_parts.append(f"Formação acadêmica inclui: {formacao[:150].strip()}...")
        if certificacoes:
            resumo_parts.append(f"Possui certificações em: {certificacoes[:100].strip()}...")

        if resumo_parts:
            resumo_profissional = " ".join(resumo_parts)
        else:
            resumo_profissional = texto_completo[:500] + "..." if len(texto_completo) > 500 else texto_completo

    return {
        'experiencia': experiencia,
        'competencias': competencias,
        'resumo_profissional': resumo_profissional,
        'formacao': formacao,
        'certificacoes': certificacoes,
        'idiomas': idiomas,
        'disponibilidade': disponibilidade,
        'beneficios_desejados': beneficios_desejados
    }


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
                dados_extraidos = processar_curriculo(texto_pdf)

                # Salvar caminho do arquivo e dados extraídos no banco
                conn = get_db_connection()
                cursor = conn.cursor()

                cursor.execute(
                    '''
                    UPDATE candidatos 
                    SET caminho_curriculo = %s, experiencia = %s, competencias = %s, resumo_profissional = %s, formacao = %s, certificacoes = %s, idiomas = %s, disponibilidade = %s, beneficios_desejados = %s
                    WHERE id = %s
                    ''',
                    (nome_arquivo, dados_extraidos['experiencia'], dados_extraidos['competencias'], dados_extraidos['resumo_profissional'], dados_extraidos['formacao'], dados_extraidos['certificacoes'], dados_extraidos['idiomas'], dados_extraidos['disponibilidade'], dados_extraidos['beneficios_desejados'], candidato_id)
                )

                conn.commit()
                conn.close()

                resultado['sucesso'] = True
                resultado['dados_extraidos'] = dados_extraidos
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
        certificacoes = request.form.get('certificacoes', '').strip()
        idiomas = request.form.get('idiomas', '').strip()
        disponibilidade = request.form.get('disponibilidade', '').strip()
        beneficios_desejados = request.form.get('beneficios_desejados', '').strip()

        if not experiencia and not competencias and not resumo_profissional and not formacao and not certificacoes and not idiomas and not disponibilidade and not beneficios_desejados:
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
            SET experiencia = %s, competencias = %s, resumo_profissional = %s, formacao = %s, certificacoes = %s, idiomas = %s, disponibilidade = %s, beneficios_desejados = %s
            WHERE id = %s
            ''',
            (experiencia, competencias, resumo_profissional, formacao, certificacoes, idiomas, disponibilidade, beneficios_desejados, candidato_id)
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