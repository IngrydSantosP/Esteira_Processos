
import sqlite3

def update_database():
    conn = sqlite3.connect('recrutamento.db')
    cursor = conn.cursor()

    try:
        # Criar tabela de categorias se não existir
        cursor.execute('''CREATE TABLE IF NOT EXISTS categorias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT UNIQUE NOT NULL
        )''')

        # Inserir categorias padrão
        categorias_padrao = [
            'Tecnologia', 'Saúde', 'Educação', 'Finanças', 'Marketing',
            'Vendas', 'Recursos Humanos', 'Administração', 'Engenharia', 'Design'
        ]

        for categoria in categorias_padrao:
            cursor.execute('INSERT OR IGNORE INTO categorias (nome) VALUES (?)', (categoria,))

        # Criar tabela de notificações se não existir
        cursor.execute('''CREATE TABLE IF NOT EXISTS notificacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidato_id INTEGER,
            empresa_id INTEGER,
            vaga_id INTEGER,
            tipo TEXT NOT NULL DEFAULT 'geral',
            titulo TEXT NOT NULL DEFAULT 'Notificação',
            mensagem TEXT NOT NULL,
            conteudo TEXT,
            lida BOOLEAN DEFAULT FALSE,
            fixada BOOLEAN DEFAULT FALSE,
            data_envio DATETIME DEFAULT CURRENT_TIMESTAMP,
            data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (candidato_id) REFERENCES candidatos (id),
            FOREIGN KEY (empresa_id) REFERENCES empresas (id),
            FOREIGN KEY (vaga_id) REFERENCES vagas (id)
        )''')

        # Criar tabela de favoritos candidato-vaga se não existir
        cursor.execute('''CREATE TABLE IF NOT EXISTS candidato_vaga_favorita (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidato_id INTEGER,
            vaga_id INTEGER,
            data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (candidato_id) REFERENCES candidatos (id),
            FOREIGN KEY (vaga_id) REFERENCES vagas (id),
            UNIQUE(candidato_id, vaga_id)
        )''')

        # Criar tabela de favoritos empresa-candidato se não existir
        cursor.execute('''CREATE TABLE IF NOT EXISTS empresa_candidato_favorito (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER,
            candidato_id INTEGER,
            vaga_id INTEGER,
            data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (empresa_id) REFERENCES empresas (id),
            FOREIGN KEY (candidato_id) REFERENCES candidatos (id),
            FOREIGN KEY (vaga_id) REFERENCES vagas (id),
            UNIQUE(empresa_id, candidato_id, vaga_id)
        )''')

        print("Tabelas de favoritos e notificações criadas com sucesso!")

        # Verificar e adicionar novas colunas nas tabelas existentes
        cursor.execute("PRAGMA table_info(vagas)")
        columns = [column[1] for column in cursor.fetchall()]

        # Adicionar colunas na tabela vagas
        colunas_vagas = {
            'status': 'ALTER TABLE vagas ADD COLUMN status TEXT DEFAULT "Ativa"',
            'data_congelamento': 'ALTER TABLE vagas ADD COLUMN data_congelamento DATE',
            'candidato_selecionado_id': 'ALTER TABLE vagas ADD COLUMN candidato_selecionado_id INTEGER',
            'candidato_contratado_id': 'ALTER TABLE vagas ADD COLUMN candidato_contratado_id INTEGER',
            'data_contratacao': 'ALTER TABLE vagas ADD COLUMN data_contratacao DATETIME',
            'ranking_contratacao': 'ALTER TABLE vagas ADD COLUMN ranking_contratacao INTEGER',
            'categoria_id': 'ALTER TABLE vagas ADD COLUMN categoria_id INTEGER REFERENCES categorias(id)',
            'urgencia_contratacao': 'ALTER TABLE vagas ADD COLUMN urgencia_contratacao TEXT',
            'data_congelamento_agendado': 'ALTER TABLE vagas ADD COLUMN data_congelamento_agendado DATE',
            'localizacao_endereco': 'ALTER TABLE vagas ADD COLUMN localizacao_endereco TEXT',
            'localizacao_cidade': 'ALTER TABLE vagas ADD COLUMN localizacao_cidade TEXT',
            'localizacao_estado': 'ALTER TABLE vagas ADD COLUMN localizacao_estado TEXT',
            'localizacao_cep': 'ALTER TABLE vagas ADD COLUMN localizacao_cep TEXT',
            'usar_endereco_empresa': 'ALTER TABLE vagas ADD COLUMN usar_endereco_empresa BOOLEAN DEFAULT FALSE',
            'diferenciais': 'ALTER TABLE vagas ADD COLUMN diferenciais TEXT',
            'endereco_vaga': 'ALTER TABLE vagas ADD COLUMN endereco_vaga TEXT'
        }

        for coluna, sql in colunas_vagas.items():
            if coluna not in columns:
                try:
                    cursor.execute(sql)
                    print(f"Coluna {coluna} adicionada à tabela vagas")
                except Exception as e:
                    print(f"Erro ao adicionar coluna {coluna}: {e}")

        # Verificar e adicionar colunas na tabela empresas
        cursor.execute("PRAGMA table_info(empresas)")
        columns_empresas = [column[1] for column in cursor.fetchall()]

        colunas_empresas = {
            'endereco': 'ALTER TABLE empresas ADD COLUMN endereco TEXT',
            'cidade': 'ALTER TABLE empresas ADD COLUMN cidade TEXT',
            'estado': 'ALTER TABLE empresas ADD COLUMN estado TEXT',
            'cep': 'ALTER TABLE empresas ADD COLUMN cep TEXT'
        }

        for coluna, sql in colunas_empresas.items():
            if coluna not in columns_empresas:
                try:
                    cursor.execute(sql)
                    print(f"Coluna {coluna} adicionada à tabela empresas")
                except Exception as e:
                    print(f"Erro ao adicionar coluna {coluna}: {e}")

        # Verificar e adicionar colunas na tabela candidatos
        cursor.execute("PRAGMA table_info(candidatos)")
        columns_candidatos = [column[1] for column in cursor.fetchall()]

        colunas_candidatos = {
            'resumo_curriculo': 'ALTER TABLE candidatos ADD COLUMN resumo_curriculo TEXT',
            'experiencia': 'ALTER TABLE candidatos ADD COLUMN experiencia TEXT',
            'competencias': 'ALTER TABLE candidatos ADD COLUMN competencias TEXT',
            'resumo_profissional': 'ALTER TABLE candidatos ADD COLUMN resumo_profissional TEXT'
        }

        for coluna, sql in colunas_candidatos.items():
            if coluna not in columns_candidatos:
                try:
                    cursor.execute(sql)
                    print(f"Coluna {coluna} adicionada à tabela candidatos")
                except Exception as e:
                    print(f"Erro ao adicionar coluna {coluna}: {e}")

        conn.commit()
        print("Banco de dados atualizado com sucesso!")

    except Exception as e:
        print(f"Erro ao atualizar banco: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    update_database()
