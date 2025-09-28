from flask import Blueprint, request, session
import os
import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv
import mysql.connector
from db import get_db_connection
from flask import jsonify


# Carrega variáveis de ambiente do .env
load_dotenv()
arquivos_bp = Blueprint('arquivos', __name__)   

# Configurações do Cloudinary
cloudinary.config(
    cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
    api_key=os.getenv('CLOUDINARY_API_KEY'),
    api_secret=os.getenv('CLOUDINARY_API_SECRET')
)

def upload_imagem_perfil(arquivo, nome_usuario=None):
    try:
        nome_publico = nome_usuario or os.path.splitext(arquivo.filename)[0]

        resultado = cloudinary.uploader.upload(
            arquivo.stream,  # usa o stream em memória
            folder='perfis',
            public_id=nome_publico,
            overwrite=True,
            resource_type='image'
        )

        return {
            'sucesso': True,
            'url': resultado.get('secure_url'),
            'public_id': resultado.get('public_id')
        }

    except Exception as e:
        return {
            'sucesso': False,
            'erro': str(e)
        }



def upload_curriculo(arquivo, nome_usuario=None):
    try:
        nome_arquivo = nome_usuario or os.path.splitext(arquivo.filename)[0]

        resultado = cloudinary.uploader.upload(
            arquivo.stream,  # usa stream em memória
            folder='curriculos',
            public_id=nome_arquivo,
            overwrite=True,
            resource_type='raw'
        )

        return {
            'sucesso': True,
            'url': resultado.get('secure_url'),
            'public_id': resultado.get('public_id'),
            'tipo': resultado.get('format'),
            'tamanho_bytes': resultado.get('bytes')
        }

    except Exception as e:
        return {
            'sucesso': False,
            'erro': str(e)
        }



@arquivos_bp.route('/upload-foto-perfil', methods=['POST'])
def rota_upload_foto_perfil():
    if 'id_usuario' not in session:
        return jsonify({'sucesso': False, 'mensagem': 'Usuário não autenticado'}), 401

    if 'imagem_perfil' not in request.files:
        return jsonify({'sucesso': False, 'mensagem': 'Arquivo "imagem_perfil" não enviado'}), 400

    imagem_perfil = request.files['imagem_perfil']

    if imagem_perfil.filename == '':
        return jsonify({'sucesso': False, 'mensagem': 'Nome de arquivo inválido'}), 400

    # Validar extensão
    extensoes_validas = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
    extensao = os.path.splitext(imagem_perfil.filename)[1].lower()
    if extensao not in extensoes_validas:
        return jsonify({'sucesso': False, 'mensagem': 'Formato de imagem não permitido'}), 400

    resultado = upload_imagem_perfil(imagem_perfil, nome_usuario=f"candidato_{session['id_usuario']}")

    if resultado['sucesso']:
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                '''
                UPDATE candidatos
                SET imagem_perfil = %s
                WHERE id = %s
                ''',
                (resultado['url'], session['id_usuario'])
            )
            conn.commit()
            cursor.close()
            conn.close()

            print(f"URL salva no banco: {resultado['url']}")  # Debug

            return jsonify({'sucesso': True, 'mensagem': 'Imagem enviada com sucesso', 'url': resultado['url']}), 200

        except Exception as e:
            print(f"Erro ao salvar no banco: {str(e)}")  # Debug
            return jsonify({'sucesso': False, 'mensagem': f"Erro ao salvar no banco de dados: {str(e)}"}), 500

    else:
        return jsonify({'sucesso': False, 'mensagem': f"Erro ao enviar imagem: {resultado['erro']}"}), 500

