
import os
import sqlite3
import PyPDF2
import re
from werkzeug.utils import secure_filename

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf'}
MAX_FILE_SIZE = 3 * 1024 * 1024  # 3MB

# Criar pasta de uploads se não existir
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def arquivo_permitido(nome_arquivo):
    """Verifica se o arquivo tem extensão permitida"""
    return '.' in nome_arquivo and nome_arquivo.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extrair_texto_pdf(caminho_arquivo):
    """Extrai texto do PDF usando PyPDF2 com melhor tratamento de erros"""
    texto_extraido = ""
    detalhes_extracao = {
        'paginas_processadas': 0,
        'erros_encontrados': [],
        'texto_vazio': False
    }
    
    try:
        with open(caminho_arquivo, 'rb') as arquivo:
            leitor = PyPDF2.PdfReader(arquivo)
            
            if len(leitor.pages) == 0:
                detalhes_extracao['erros_encontrados'].append("PDF não contém páginas")
                return texto_extraido, detalhes_extracao
            
            for i, pagina in enumerate(leitor.pages):
                try:
                    texto_pagina = pagina.extract_text()
                    if texto_pagina:
                        texto_extraido += texto_pagina + "\n"
                        detalhes_extracao['paginas_processadas'] += 1
                    else:
                        detalhes_extracao['erros_encontrados'].append(f"Página {i+1} está vazia ou não foi possível extrair texto")
                except Exception as e:
                    detalhes_extracao['erros_encontrados'].append(f"Erro na página {i+1}: {str(e)}")
                    
        if not texto_extraido.strip():
            detalhes_extracao['texto_vazio'] = True
            
    except Exception as e:
        detalhes_extracao['erros_encontrados'].append(f"Erro ao processar PDF: {str(e)}")
    
    return texto_extraido, detalhes_extracao

def processar_curriculo_inteligente(texto_curriculo):
    """Processa o texto do currículo para extrair informações com melhor precisão"""
    resultado = {
        'experiencia': "",
        'competencias': "",
        'resumo_profissional': "",
        'informacoes_encontradas': []
    }
    
    texto_lower = texto_curriculo.lower()
    
    # Padrões mais abrangentes para experiência profissional
    padroes_experiencia = [
        r'experiência[^:]*:(.+?)(?=\n\n|\ncompetências|\nhabilidades|\nformação|\neducação|$)',
        r'experiência profissional[^:]*:(.+?)(?=\n\n|\ncompetências|\nhabilidades|\nformação|$)',
        r'histórico profissional[^:]*:(.+?)(?=\n\n|\ncompetências|\nhabilidades|\nformação|$)',
        r'carreira[^:]*:(.+?)(?=\n\n|\ncompetências|\nhabilidades|\nformação|$)',
        r'trabalho[^:]*:(.+?)(?=\n\n|\ncompetências|\nhabilidades|\nformação|$)'
    ]
    
    for i, padrao in enumerate(padroes_experiencia):
        match = re.search(padrao, texto_lower, re.DOTALL)
        if match:
            resultado['experiencia'] = match.group(1).strip()
            resultado['informacoes_encontradas'].append(f"Experiência encontrada usando padrão {i+1}")
            break
    
    # Padrões para competências/habilidades
    padroes_competencias = [
        r'competências[^:]*:(.+?)(?=\n\n|\nexperiência|\nformação|\neducação|$)',
        r'habilidades[^:]*:(.+?)(?=\n\n|\nexperiência|\nformação|\neducação|$)',
        r'conhecimentos[^:]*:(.+?)(?=\n\n|\nexperiência|\nformação|\neducação|$)',
        r'skills[^:]*:(.+?)(?=\n\n|\nexperiência|\nformação|\neducação|$)',
        r'tecnologias[^:]*:(.+?)(?=\n\n|\nexperiência|\nformação|\neducação|$)'
    ]
    
    for i, padrao in enumerate(padroes_competencias):
        match = re.search(padrao, texto_lower, re.DOTALL)
        if match:
            resultado['competencias'] = match.group(1).strip()
            resultado['informacoes_encontradas'].append(f"Competências encontradas usando padrão {i+1}")
            break
    
    # Padrões para resumo profissional
    padroes_resumo = [
        r'resumo[^:]*:(.+?)(?=\n\n|\nexperiência|\ncompetências|\nformação|$)',
        r'objetivo[^:]*:(.+?)(?=\n\n|\nexperiência|\ncompetências|\nformação|$)',
        r'perfil[^:]*:(.+?)(?=\n\n|\nexperiência|\ncompetências|\nformação|$)',
        r'sobre[^:]*:(.+?)(?=\n\n|\nexperiência|\ncompetências|\nformação|$)',
        r'apresentação[^:]*:(.+?)(?=\n\n|\nexperiência|\ncompetências|\nformação|$)'
    ]
    
    for i, padrao in enumerate(padroes_resumo):
        match = re.search(padrao, texto_lower, re.DOTALL)
        if match:
            resultado['resumo_profissional'] = match.group(1).strip()
            resultado['informacoes_encontradas'].append(f"Resumo encontrado usando padrão {i+1}")
            break
    
    # Se não encontrou informações estruturadas, tentar extrair do texto livre
    if not resultado['experiencia'] and not resultado['competencias'] and not resultado['resumo_profissional']:
        # Pegar as primeiras linhas como resumo
        linhas = texto_curriculo.split('\n')
        primeiras_linhas = []
        for linha in linhas[:10]:  # Primeiras 10 linhas
            if linha.strip() and len(linha.strip()) > 20:
                primeiras_linhas.append(linha.strip())
        
        if primeiras_linhas:
            resultado['resumo_profissional'] = ' '.join(primeiras_linhas[:3])
            resultado['informacoes_encontradas'].append("Resumo extraído das primeiras linhas do documento")
    
    return resultado

def processar_upload_curriculo(request, candidato_id):
    """Processa o upload do currículo com validação e feedback detalhado"""
    resultado = {
        'sucesso': False,
        'dados_extraidos': {},
        'mensagens': []
    }
    
    try:
        # Verificar se arquivo foi enviado
        if 'arquivo' not in request.files:
            resultado['mensagens'].append({
                'texto': 'Nenhum arquivo foi selecionado. Por favor, escolha um arquivo PDF.',
                'tipo': 'error'
            })
            return resultado
        
        arquivo = request.files['arquivo']
        
        if arquivo.filename == '':
            resultado['mensagens'].append({
                'texto': 'Nenhum arquivo foi selecionado. Por favor, escolha um arquivo PDF.',
                'tipo': 'error'
            })
            return resultado
        
        # Verificar extensão
        if not arquivo_permitido(arquivo.filename):
            resultado['mensagens'].append({
                'texto': 'Apenas arquivos PDF são aceitos. Por favor, converta seu currículo para PDF.',
                'tipo': 'error'
            })
            return resultado
        
        # Verificar tamanho do arquivo
        arquivo.seek(0, os.SEEK_END)
        tamanho_arquivo = arquivo.tell()
        arquivo.seek(0)
        
        if tamanho_arquivo > MAX_FILE_SIZE:
            resultado['mensagens'].append({
                'texto': f'Arquivo muito grande ({tamanho_arquivo/1024/1024:.1f}MB). O tamanho máximo é 3MB.',
                'tipo': 'error'
            })
            return resultado
        
        # Salvar arquivo temporariamente
        nome_arquivo = secure_filename(arquivo.filename)
        caminho_arquivo = os.path.join(UPLOAD_FOLDER, f"temp_candidato_{candidato_id}_{nome_arquivo}")
        arquivo.save(caminho_arquivo)
        
        # Extrair texto do PDF
        texto_curriculo, detalhes_extracao = extrair_texto_pdf(caminho_arquivo)
        
        # Remover arquivo temporário
        if os.path.exists(caminho_arquivo):
            os.remove(caminho_arquivo)
        
        # Verificar se foi possível extrair texto
        if detalhes_extracao['texto_vazio'] or not texto_curriculo.strip():
            resultado['mensagens'].append({
                'texto': 'Não foi possível extrair texto do PDF. Verifique se o arquivo não está protegido ou escaneado como imagem.',
                'tipo': 'error'
            })
            if detalhes_extracao['erros_encontrados']:
                for erro in detalhes_extracao['erros_encontrados']:
                    resultado['mensagens'].append({
                        'texto': f"Detalhe: {erro}",
                        'tipo': 'warning'
                    })
            return resultado
        
        # Processar currículo
        dados_processados = processar_curriculo_inteligente(texto_curriculo)
        
        # Salvar texto original no banco
        conn = sqlite3.connect('recrutamento.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE candidatos 
            SET texto_curriculo = ?
            WHERE id = ?
        ''', (texto_curriculo, candidato_id))
        
        conn.commit()
        conn.close()
        
        # Preparar feedback para o usuário
        resultado['sucesso'] = True
        resultado['dados_extraidos'] = dados_processados
        
        resultado['mensagens'].append({
            'texto': f'PDF processado com sucesso! {detalhes_extracao["paginas_processadas"]} página(s) analisada(s).',
            'tipo': 'success'
        })
        
        if dados_processados['informacoes_encontradas']:
            for info in dados_processados['informacoes_encontradas']:
                resultado['mensagens'].append({
                    'texto': f"✓ {info}",
                    'tipo': 'info'
                })
        
        if not dados_processados['experiencia'] and not dados_processados['competencias'] and not dados_processados['resumo_profissional']:
            resultado['mensagens'].append({
                'texto': 'Não foi possível identificar seções estruturadas no currículo. Por favor, preencha as informações manualmente.',
                'tipo': 'warning'
            })
        
        if detalhes_extracao['erros_encontrados']:
            resultado['mensagens'].append({
                'texto': f'Alguns problemas foram encontrados durante o processamento, mas o texto principal foi extraído.',
                'tipo': 'warning'
            })
    
    except Exception as e:
        resultado['mensagens'].append({
            'texto': f'Erro inesperado ao processar arquivo: {str(e)}',
            'tipo': 'error'
        })
        
        # Limpar arquivo temporário em caso de erro
        try:
            if 'caminho_arquivo' in locals() and os.path.exists(caminho_arquivo):
                os.remove(caminho_arquivo)
        except:
            pass
    
    return resultado

def finalizar_processamento_curriculo(request, candidato_id):
    """Finaliza o processamento do currículo salvando as informações editadas"""
    resultado = {
        'sucesso': False,
        'mensagens': []
    }
    
    try:
        experiencia = request.form.get('experiencia', '').strip()
        competencias = request.form.get('competencias', '').strip()
        resumo_profissional = request.form.get('resumo_profissional', '').strip()
        
        # Validar se pelo menos um campo foi preenchido
        if not experiencia and not competencias and not resumo_profissional:
            resultado['mensagens'].append({
                'texto': 'Por favor, preencha pelo menos um dos campos antes de finalizar.',
                'tipo': 'error'
            })
            return resultado
        
        # Salvar no banco
        conn = sqlite3.connect('recrutamento.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE candidatos 
            SET experiencia = ?, competencias = ?, resumo_profissional = ?
            WHERE id = ?
        ''', (experiencia, competencias, resumo_profissional, candidato_id))
        
        conn.commit()
        conn.close()
        
        resultado['sucesso'] = True
        resultado['mensagens'].append({
            'texto': 'Currículo processado e salvo com sucesso! Agora você pode ver as vagas recomendadas.',
            'tipo': 'success'
        })
        
    except Exception as e:
        resultado['mensagens'].append({
            'texto': f'Erro ao salvar informações do currículo: {str(e)}',
            'tipo': 'error'
        })
    
    return resultado
