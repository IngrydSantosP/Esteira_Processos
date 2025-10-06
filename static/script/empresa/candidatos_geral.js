let todosCandidatos = [];
let candidatosFiltrados = [];
let paginaAtual = 1;
const candidatosPorPagina = 12;

// Carregar todos os candidatos
async function carregarCandidatos() {
    try {
        const response = await fetch('/api/candidatos-geral');
        if (!response.ok) throw new Error('Erro na requisição');

        todosCandidatos = await response.json();
        candidatosFiltrados = [...todosCandidatos];

        atualizarEstatisticas();
        renderizarCandidatos();

    } catch (error) {
        console.error('Erro ao carregar candidatos:', error);
        document.getElementById('candidatosList').innerHTML = `        
            <div class="message-container">
                <div class="error-icon">
                    <span class="error-symbol">❌</span>
                </div>
                <h3 class="error-title">Erro ao carregar candidatos</h3>
                <p class="error-description">Tente recarregar a página.</p>
            </div>
        `;
    }
}

// Atualizar estatísticas
function atualizarEstatisticas() {
    document.getElementById('totalCandidatos').textContent = todosCandidatos.length;
    document.getElementById('comCurriculo').textContent = todosCandidatos.filter(c => c.tem_curriculo).length;
    document.getElementById('totalFavoritados').textContent = todosCandidatos.filter(c => c.is_favorito).length;
}

// Aplicar filtros
function aplicarFiltros() {
    const searchTerm = document.getElementById('searchInput').value.toLowerCase();
    const salarioRange = document.getElementById('salarioFilter').value;
    const location = document.getElementById('locationFilter').value.toLowerCase();
    const skills = document.getElementById('skillsFilter').value.toLowerCase();

    candidatosFiltrados = todosCandidatos.filter(candidato => {
        const matchSearch = !searchTerm || 
            candidato.nome.toLowerCase().includes(searchTerm) ||
            candidato.email.toLowerCase().includes(searchTerm);

        let matchSalario = true;
        if (salarioRange) {
            const [min, max] = salarioRange.split('-').map(Number);
            const salario = candidato.pretensao_salarial || 0;
            matchSalario = salario >= min && salario <= max;
        }

        const matchLocation = !location || candidato.endereco_completo.toLowerCase().includes(location);
        const matchSkills = !skills || (candidato.competencias && candidato.competencias.toLowerCase().includes(skills)) ||
            (candidato.texto_curriculo && candidato.texto_curriculo.toLowerCase().includes(skills));

        return matchSearch && matchSalario && matchLocation && matchSkills;
    });

    paginaAtual = 1;
    renderizarCandidatos();
}

// Limpar filtros
function limparFiltros() {
    document.getElementById('searchInput').value = '';
    document.getElementById('salarioFilter').value = '';
    document.getElementById('locationFilter').value = '';
    document.getElementById('skillsFilter').value = '';
    
    candidatosFiltrados = [...todosCandidatos];
    paginaAtual = 1;
    renderizarCandidatos();
}

// Renderizar candidatos com paginação
function renderizarCandidatos() {
    const container = document.getElementById('candidatosList');
    const inicio = (paginaAtual - 1) * candidatosPorPagina;
    const fim = inicio + candidatosPorPagina;
    const candidatosPagina = candidatosFiltrados.slice(inicio, fim);

    if (candidatosFiltrados.length === 0) {
        container.innerHTML = `        
            <div class="message-container">
                <div class="no-results-icon">
                    <span class="no-results-symbol">🔍</span>
                </div>
                <h3 class="no-results-title">Nenhum candidato encontrado</h3>
                <p class="no-results-description">Tente ajustar os filtros de busca.</p>
                <button onclick="limparFiltros()" class="clear-filters-button">Limpar Filtros</button>
            </div>
        `;
        document.getElementById('paginacao').classList.add('hidden');
        return;
    }

    let html = '';

    candidatosPagina.forEach(candidato => {
        const salarioFormatado = candidato.pretensao_salarial ? 
            new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(candidato.pretensao_salarial) : 
            'Não informado';

        html += `
            <div class="candidato-card">
                <div class="candidato-header">
                    <div class="candidato-info">
                        <div class="avatar">
                            <span class="avatar-icon">👤</span>
                        </div>
                        <div class="name-star">
                            <h3 class="candidato-name">${candidato.nome}</h3>
                            <button onclick="toggleFavorito(${candidato.id}, this)" 
                                    data-favorito="${candidato.is_favorito}" 
                                    class="favorite-button ${candidato.is_favorito ? 'favorited' : 'not-favorited'}">
                                ${candidato.is_favorito ? '⭐' : '☆'}
                            </button>
                        </div>
                        <p class="candidato-email">${candidato.email}</p>
                    </div>
                </div>

                <div class="candidato-details">
                    <div class="detail-item">
                        <span class="detail-icon">💰</span>
                        <span class="detail-text">Pretensão: ${salarioFormatado}</span>
                    </div>

                    ${candidato.telefone ? `        
                        <div class="detail-item">
                            <span class="detail-icon">📱</span>
                            <span class="detail-text">${candidato.telefone}</span>
                        </div>
                    ` : ''}

                    ${candidato.endereco_completo ? `
                        <div class="detail-item">
                            <span class="detail-icon">📍</span>
                            <span class="detail-text">${candidato.endereco_completo}</span>
                        </div>
                    ` : ''}

                </div>

                <div class="candidato-actions">
                    ${candidato.tem_curriculo ? `
                        <a href="/baixar_curriculo/${candidato.id}" class="curriculo-button">📄 Currículo</a>
                    ` : `
                        <div class="no-curriculo">Sem currículo</div>
                    `}
                    ${candidato.linkedin ? `
                        <a href="${candidato.linkedin}" target="_blank" class="linkedin-button">🔗</a>
                    ` : ''}
                </div>
            </div>
        `;
    });

    container.innerHTML = html;

    // Atualizar paginação
    atualizarPaginacao();
}

// Atualizar paginação
function atualizarPaginacao() {
    const totalPaginas = Math.ceil(candidatosFiltrados.length / candidatosPorPagina);
    
    if (totalPaginas <= 1) {
        document.getElementById('paginacao').classList.add('hidden');
        return; 
    }

    document.getElementById('paginacao').classList.remove('hidden');
    document.getElementById('infoPagina').textContent = `Página ${paginaAtual} de ${totalPaginas}`;
    
    document.getElementById('btnAnterior').disabled = paginaAtual === 1;
    document.getElementById('btnProximo').disabled = paginaAtual === totalPaginas;
}

// Navegação de páginas
function anteriorPagina() {
    if (paginaAtual > 1) {
        paginaAtual--;
        renderizarCandidatos();
    }
}

function proximaPagina() {
    const totalPaginas = Math.ceil(candidatosFiltrados.length / candidatosPorPagina);
    if (paginaAtual < totalPaginas) {
        paginaAtual++;
        renderizarCandidatos();
    }
}

// Toggle favorito
async function toggleFavorito(candidatoId, button) {
    const isFavorito = button.dataset.favorito === 'true';

    try {
        button.classList.add('pulse-animation');

        const response = await fetch('/api/favoritar-candidato-geral', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                candidato_id: candidatoId,
                acao: 'toggle'
            })
        });

        const result = await response.json();

        if (result.success) {
            button.dataset.favorito = result.favorited;
            button.textContent = result.favorited ? '⭐' : '☆';
            button.className = `favorite-button ${result.favorited ? 'favorited' : 'not-favorited'}`;

            // Atualizar na lista local
            const candidato = todosCandidatos.find(c => c.id === candidatoId);
            if (candidato) {
                candidato.is_favorito = result.favorited;
            }

            atualizarEstatisticas();
            showToast(result.message, 'success');
        } else {
            showToast(result.message || 'Erro ao favoritar candidato', 'error');
        }
    } catch (error) {
        console.error('Erro ao favoritar:', error);
        showToast('Erro ao favoritar candidato', 'error');
    } finally {
        button.classList.remove('pulse-animation');
    }
}

// Toast notifications
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;

    document.body.appendChild(toast);

    setTimeout(() => {
        toast.classList.add('show');
    }, 100);

    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => {
            document.body.removeChild(toast);
        }, 300);
    }, 3000);
}

// Busca em tempo real
document.getElementById('searchInput').addEventListener('input', function() {
    aplicarFiltros();
});

// Carregar candidatos quando a página carregar
document.addEventListener('DOMContentLoaded', function() {
    carregarCandidatos();
});
