
import sqlite3
from datetime import datetime

def inicializar_banco():
    """Inicializa o banco de dados SQLite"""
    conn = sqlite3.connect('recrutamento.db')
    cursor = conn.cursor()
    
    # Tabela empresas
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS empresas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cnpj TEXT UNIQUE NOT NULL,
            nome TEXT NOT NULL,
            email TEXT NOT NULL,
            senha_hash TEXT NOT NULL
        )
    ''')
    
    # Tabela candidatos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS candidatos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            email TEXT NOT NULL,
            senha_hash TEXT NOT NULL,
            telefone TEXT,
            linkedin TEXT,
            pretensao_salarial REAL,
            texto_curriculo TEXT,
            experiencia TEXT,
            competencias TEXT,
            resumo_profissional TEXT
        )
    ''')
    
    # Tabela vagas
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS vagas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            titulo TEXT NOT NULL,
            descricao TEXT NOT NULL,
            requisitos TEXT NOT NULL,
            salario_oferecido REAL NOT NULL,
            data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (empresa_id) REFERENCES empresas (id)
        )
    ''')
    
    # Tabela candidaturas
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS candidaturas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidato_id INTEGER NOT NULL,
            vaga_id INTEGER NOT NULL,
            score REAL NOT NULL,
            posicao INTEGER,
            data_candidatura DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (candidato_id) REFERENCES candidatos (id),
            FOREIGN KEY (vaga_id) REFERENCES vagas (id)
        )
    ''')
    
    conn.commit()
    conn.close()

def atualizar_posicoes_candidatura(vaga_id):
    """Atualiza as posições dos candidatos para uma vaga específica"""
    conn = sqlite3.connect('recrutamento.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, score FROM candidaturas 
        WHERE vaga_id = ? 
        ORDER BY score DESC
    ''', (vaga_id,))
    
    candidaturas = cursor.fetchall()
    
    for posicao, (candidatura_id, score) in enumerate(candidaturas, 1):
        cursor.execute('''
            UPDATE candidaturas 
            SET posicao = ? 
            WHERE id = ?
        ''', (posicao, candidatura_id))
    
    conn.commit()
    conn.close()

def processar_candidatura(candidato_id, vaga_id, modo_ia):
    """Processa uma candidatura e retorna resultado"""
    from avaliador import criar_avaliador
    
    conn = sqlite3.connect('recrutamento.db')
    cursor = conn.cursor()
    
    resultado = {
        'sucesso': False,
        'mensagens': []
    }
    
    try:
        # Verificar se já se candidatou
        cursor.execute('''
            SELECT id FROM candidaturas 
            WHERE candidato_id = ? AND vaga_id = ?
        ''', (candidato_id, vaga_id))
        
        if cursor.fetchone():
            resultado['mensagens'].append({
                'texto': 'Você já se candidatou para esta vaga',
                'tipo': 'info'
            })
            return resultado
        
        # Buscar dados do candidato e da vaga
        cursor.execute('''
            SELECT pretensao_salarial, texto_curriculo 
            FROM candidatos 
            WHERE id = ?
        ''', (candidato_id,))
        candidato = cursor.fetchone()
        
        cursor.execute('''
            SELECT requisitos, salario_oferecido 
            FROM vagas 
            WHERE id = ?
        ''', (vaga_id,))
        vaga = cursor.fetchone()
        
        if candidato and vaga:
            # Calcular score
            avaliador = criar_avaliador(modo_ia)
            score = avaliador.calcular_score(
                candidato[1], 
                vaga[0], 
                candidato[0], 
                vaga[1]
            )
            
            # Inserir candidatura
            cursor.execute('''
                INSERT INTO candidaturas (candidato_id, vaga_id, score)
                VALUES (?, ?, ?)
            ''', (candidato_id, vaga_id, score))
            
            conn.commit()
            
            # Atualizar posições
            atualizar_posicoes_candidatura(vaga_id)
            
            # Buscar posição atual
            cursor.execute('''
                SELECT posicao FROM candidaturas 
                WHERE candidato_id = ? AND vaga_id = ?
            ''', (candidato_id, vaga_id))
            posicao = cursor.fetchone()[0]
            
            resultado['sucesso'] = True
            resultado['mensagens'].append({
                'texto': f'Candidatura realizada com sucesso! Você está na posição {posicao}',
                'tipo': 'success'
            })
        else:
            resultado['mensagens'].append({
                'texto': 'Erro ao processar candidatura',
                'tipo': 'error'
            })
    
    except Exception as e:
        resultado['mensagens'].append({
            'texto': f'Erro ao processar candidatura: {str(e)}',
            'tipo': 'error'
        })
    finally:
        conn.close()
    
    return resultado
