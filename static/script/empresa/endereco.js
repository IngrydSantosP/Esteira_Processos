document.addEventListener('DOMContentLoaded', function() {
    const categoriaSelect = document.getElementById('categoria_id');
    const novaCategoriaDiv = document.getElementById('nova-categoria-div');
    const usarEnderecoEmpresa = document.getElementById('usar_endereco_empresa');

    // Mostrar/ocultar campo de nova categoria
    categoriaSelect.addEventListener('change', function() {
        if (this.value === 'nova') {
            novaCategoriaDiv.style.display = 'block';
        } else {
            novaCategoriaDiv.style.display = 'none';
        }
    });

    // Carregar endereço da empresa
    usarEnderecoEmpresa.addEventListener('change', function() {
        if (this.checked) {
            fetch('/empresa/endereco')
                .then(response => response.json())
                .then(data => {
                    if (!data.error) {
                        document.getElementById('localizacao_endereco').value = data.endereco || '';
                        document.getElementById('localizacao_cidade').value = data.cidade || '';
                        document.getElementById('localizacao_estado').value = data.estado || '';
                        document.getElementById('localizacao_cep').value = data.cep || '';
                    }
                })
                .catch(error => console.error('Erro:', error));
        }
    });

    // Verificar se deve mostrar nova categoria no carregamento
    if (categoriaSelect.value === 'nova') {
        novaCategoriaDiv.style.display = 'block';
    }
});