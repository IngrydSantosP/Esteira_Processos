import mysql.connector
from mysql.connector import Error
from db import get_db_connection
from datetime import datetime
import random


def inicializar_banco():
    """Inicializa o banco de dados MySQL com todas as tabelas necessárias"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Criar tabela de candidatos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS candidatos (
            id INT AUTO_INCREMENT PRIMARY KEY,
            nome VARCHAR(255) NOT NULL,
            email VARCHAR(255) UNIQUE NOT NULL,
            senha_hash VARCHAR(255) NOT NULL,
            telefone VARCHAR(50),
            linkedin VARCHAR(255),
            endereco TEXT,
            pretensao_salarial DECIMAL(10,2),
            resumo_profissional TEXT,
            caminho_curriculo TEXT,
            experiencia TEXT,
            competencias TEXT,
            resumo_profissional TEXT
        )
    ''')

    # Criar tabela de empresas
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS empresas (
            id INT AUTO_INCREMENT PRIMARY KEY,
            cnpj VARCHAR(50) UNIQUE NOT NULL,
            nome VARCHAR(255) NOT NULL,
            email VARCHAR(255) UNIQUE NOT NULL,
            senha_hash VARCHAR(255) NOT NULL
        )
    ''')

    # Criar tabela de vagas
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS vagas (
            id INT AUTO_INCREMENT PRIMARY KEY,
            empresa_id INT NOT NULL,
            titulo VARCHAR(255) NOT NULL,
            descricao TEXT NOT NULL,
            requisitos TEXT NOT NULL,
            salario_oferecido DECIMAL(10,2) NOT NULL,
            data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            tipo_vaga ENUM('Presencial','Remoto','Híbrido') DEFAULT 'Presencial',
            endereco_vaga TEXT,
            status ENUM('Ativa','Inativa','Congelada') DEFAULT 'Ativa',
            candidato_selecionado_id INT,
            diferenciais TEXT,
            FOREIGN KEY (empresa_id) REFERENCES empresas (id),
            FOREIGN KEY (candidato_selecionado_id) REFERENCES candidatos (id)
        )
    ''')

    # Criar tabela de candidaturas
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS candidaturas (
            id INT AUTO_INCREMENT PRIMARY KEY,
            candidato_id INT NOT NULL,
            vaga_id INT NOT NULL,
            data_candidatura TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            score DECIMAL(5,2) DEFAULT 0,
            posicao INT DEFAULT 0,
            FOREIGN KEY (candidato_id) REFERENCES candidatos (id),
            FOREIGN KEY (vaga_id) REFERENCES vagas (id)
        )
    ''')

    # Criar tabela de notificações
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notificacoes (
            id INT AUTO_INCREMENT PRIMARY KEY,
            candidato_id INT NOT NULL,
            empresa_id INT NOT NULL,
            vaga_id INT NOT NULL,
            mensagem TEXT NOT NULL,
            data_envio TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            lida BOOLEAN DEFAULT FALSE,
            FOREIGN KEY (candidato_id) REFERENCES candidatos (id),
            FOREIGN KEY (empresa_id) REFERENCES empresas (id),
            FOREIGN KEY (vaga_id) REFERENCES vagas (id)
        )
    ''')

    conn.commit()
    conn.close()


def atualizar_posicoes_candidatura(vaga_id):
    """Atualiza as posições dos candidatos para uma vaga específica"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, score FROM candidaturas 
        WHERE vaga_id = %s 
        ORDER BY score DESC
        """, (vaga_id,)
    )
    candidaturas = cursor.fetchall()

    for posicao, (candidatura_id, score) in enumerate(candidaturas, 1):
        cursor.execute(
            """
            UPDATE candidaturas 
            SET posicao = %s 
            WHERE id = %s
            """, (posicao, candidatura_id)
        )

    conn.commit()
    conn.close()


def calcular_distancia_endereco(endereco1, endereco2):
    """Calcula distância entre dois endereços (implementação simplificada)"""
    if endereco1 and endereco2:
        return random.uniform(1.0, 50.0)  # Simulação (1 a 50 km)
    return None


def processar_candidatura(candidato_id, vaga_id, modo_ia='local'):
    """Processar candidatura do candidato à vaga"""
    from avaliador import criar_avaliador
    from utils.notifications import notification_system

    mensagens = []

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Verificar se já existe candidatura
        cursor.execute(
            """
            SELECT id FROM candidaturas 
            WHERE candidato_id = %s AND vaga_id = %s
            """, (candidato_id, vaga_id)
        )
        if cursor.fetchone():
            mensagens.append({
                'texto': 'Você já se candidatou para esta vaga',
                'tipo': 'info'
            })
            return {'sucesso': False, 'mensagens': mensagens}

        # Buscar dados do candidato
        cursor.execute(
            """
            SELECT pretensao_salarial, resumo_profissional, endereco
            FROM candidatos 
            WHERE id = %s
            """, (candidato_id,)
        )
        candidato = cursor.fetchone()

        # Buscar dados da vaga
        cursor.execute(
            """
            SELECT requisitos, salario_oferecido, tipo_vaga, endereco_vaga, diferenciais, titulo
            FROM vagas 
            WHERE id = %s AND (status IS NULL OR status = 'Ativa')
            """, (vaga_id,)
        )
        vaga = cursor.fetchone()

        if not vaga:
            mensagens.append({
                'texto': 'Vaga não encontrada ou não está ativa',
                'tipo': 'error'
            })
            return {'sucesso': False, 'mensagens': mensagens}

        if candidato and vaga:
            avaliador = criar_avaliador(modo_ia)
            score = avaliador.calcular_score(
                candidato[1],  # resumo_profissional
                vaga[0],       # requisitos
                candidato[0],  # pretensao_salarial
                vaga[1],       # salario_oferecido
                vaga[4],       # diferenciais
                candidato[2],  # endereco
                vaga[3],       # endereco_vaga
                vaga[2]        # tipo_vaga
            )

            # Ajustar score pela distância
            if vaga[2] in ['Presencial', 'Híbrido'] and candidato[2] and vaga[3]:
                distancia = calcular_distancia_endereco(candidato[2], vaga[3])
                if distancia:
                    if distancia <= 5:
                        score += 10
                    elif distancia <= 15:
                        score += 5
                    elif distancia <= 30:
                        score += 2

            score = min(score, 100)

            # Inserir candidatura
            cursor.execute(
                """
                INSERT INTO candidaturas (candidato_id, vaga_id, score)
                VALUES (%s, %s, %s)
                """, (candidato_id, vaga_id, score)
            )
            conn.commit()

            # Atualizar posições
            atualizar_posicoes_candidatura(vaga_id)

            # Buscar posição atual
            cursor.execute(
                """
                SELECT posicao FROM candidaturas 
                WHERE candidato_id = %s AND vaga_id = %s
                """, (candidato_id, vaga_id)
            )
            posicao = cursor.fetchone()[0]

            # Criar notificação
            notification_system.notificar_nova_candidatura(
                candidato_id, vaga_id, posicao, score
            )

            mensagens.append({
                'texto':
                f'Candidatura realizada com sucesso! Você está na posição {posicao} com score de {score:.1f}%.',
                'tipo': 'success'
            })

            return {'sucesso': True, 'mensagens': mensagens}

    except Exception as e:
        mensagens.append({
            'texto': f'Erro ao processar candidatura: {str(e)}',
            'tipo': 'error'
        })
        return {'sucesso': False, 'mensagens': mensagens}

    finally:
        conn.close()
