window.candidatosFavoritos = window.candidatosFavoritos || [];
window.candidatosFiltrados = window.candidatosFiltrados || [];

// Carrega candidatos favoritos da API
async function loadCandidatosFavoritos() {
    const container = document.getElementById('candidatosList');
    if (!container) return;

    try {
        const response = await fetch('/api/candidatos-favoritos');
        if (!response.ok) throw new Error('Erro na requisição');

        window.candidatosFavoritos = await response.json();
        window.candidatosFiltrados = [...window.candidatosFavoritos];

        updateStats();
        populateVagaFilter();
        renderCandidatos(
            console.log("Favoritos:", window.candidatosFavoritos);
console.log("Filtrados:", window.candidatosFiltrados);
        );

    } catch (error) {
        console.error('Erro ao carregar favoritos:', error);
        container.innerHTML = `
            <div class="text-center py-12 bg-white rounded-2xl shadow-sm border border-gray-100">
                <div class="w-24 h-24 bg-yellow-100 rounded-full mx-auto mb-6 flex items-center justify-center">
                    <span class="text-4xl">❌</span>
                </div>
                <h3 class="text-xl font-bold text-gray-600 mb-3">Erro ao carregar favoritos</h3>
                <p class="text-gray-500">Tente recarregar a página.</p>
            </div>
        `;
    }
}

// Atualiza o contador de favoritos
function updateStats() {
    const totalEl = document.getElementById('totalFavoritos');
    if (totalEl) totalEl.textContent = window.candidatosFavoritos.length;
}

// Preenche filtro de vagas
function populateVagaFilter() {
    const vagaFilter = document.getElementById('vagaFilter');
    if (!vagaFilter) return;

    const vagas = [...new Set(window.candidatosFavoritos.map(c => c.vaga_titulo))];
    vagaFilter.innerHTML = '<option value="">Todas as vagas</option>';
    vagas.forEach(vaga => {
        const option = document.createElement('option');
        option.value = vaga;
        option.textContent = vaga;
        vagaFilter.appendChild(option);
    });
}

// Aplica filtros de busca e vaga
function aplicarFiltros() {
    const searchInput = document.getElementById('searchInput');
    const vagaFilter = document.getElementById('vagaFilter');
    if (!searchInput || !vagaFilter) return;

    const searchTerm = searchInput.value.toLowerCase();
    const vagaSelecionada = vagaFilter.value;

    window.candidatosFiltrados = window.candidatosFavoritos.filter(candidato => {
        const matchSearch = !searchTerm || candidato.nome.toLowerCase().includes(searchTerm);
        const matchVaga = !vagaSelecionada || candidato.vaga_titulo === vagaSelecionada;
        return matchSearch && matchVaga;
    });

    renderCandidatos();
}

// Renderiza candidatos na tela
function renderCandidatos() {
    const container = document.getElementById('candidatosList');
    if (!container) return;

    if (window.candidatosFiltrados.length === 0) {
        if (window.candidatosFavoritos.length === 0) {
            container.innerHTML = `
                <div class="text-center py-12 bg-white rounded-2xl shadow-sm border border-gray-100">
                    <div class="w-24 h-24 bg-gray-100 rounded-full mx-auto mb-6 flex items-center justify-center">
                        <span class="text-4xl">⭐</span>
                    </div>
                    <h3 class="text-xl font-bold text-gray-600 mb-3">Nenhum candidato favorito ainda</h3>
                    <p class="text-gray-500 mb-6">Favorite candidatos nas páginas de vagas para vê-los aqui.</p>
                    <a href="${DASHBOARD_VAGAS_URL}"
                       class="bg-gradient-to-r from-yellow-500 to-orange-500 hover:from-yellow-600 hover:to-orange-600 text-white px-6 py-3 rounded-xl font-semibold transition-all duration-300 transform hover:scale-105 inline-flex items-center gap-2">
                        <span>🏢</span>
                        Ver Vagas
                    </a>
                </div>
            `;
        } else {
            container.innerHTML = `
                <div class="text-center py-12 bg-white rounded-2xl shadow-sm border border-gray-100">
                    <div class="w-24 h-24 bg-gray-100 rounded-full mx-auto mb-6 flex items-center justify-center">
                        <span class="text-4xl">🔍</span>
                    </div>
                    <h3 class="text-xl font-bold text-gray-600 mb-3">Nenhum resultado encontrado</h3>
                    <p class="text-gray-500 mb-6">Tente ajustar os filtros de busca.</p>
                    <button onclick="limparFiltros()"
                            class="bg-gray-500 hover:bg-gray-600 text-white px-6 py-3 rounded-xl font-semibold transition-all duration-300">
                        Limpar Filtros
                    </button>
                </div>
            `;
        }
        return;
    }

    let html = '<div class="grid gap-6">';
    window.candidatosFiltrados.forEach(candidato => {
        const dataFavorito = candidato.data_favorito ? new Date(candidato.data_favorito).toLocaleDateString('pt-BR') : '-';
        html += `
            <div class="bg-white rounded-2xl p-6 shadow-sm border border-gray-100 hover:shadow-lg hover:border-yellow-200 transition-all duration-300 candidato-favorito-card" data-vaga-id="${candidato.vaga_id}">
                <div class="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
                    <div class="flex-1">
                        <div class="flex items-start gap-4">
                            <div class="w-16 h-16 bg-gradient-to-br from-yellow-100 to-orange-100 rounded-xl flex items-center justify-center flex-shrink-0">
                                <span class="text-2xl">👤</span>
                            </div>
                            <div class="flex-1">
                                <div class="flex items-center gap-3 mb-2">
                                    <h3 class="text-xl font-bold text-gray-800">${candidato.nome}</h3>
                                    <span class="bg-yellow-100 text-yellow-800 px-2 py-1 rounded-full text-xs font-medium">⭐ Favorito</span>
                                </div>
                                <p class="text-purple-600 font-semibold mb-2 flex items-center gap-2">
                                    <span class="w-4 h-4 bg-purple-100 rounded-full flex items-center justify-center text-xs">
                                        ${candidato.vaga_titulo === 'Favorito Geral' ? '⭐' : '💼'}
                                    </span>
                                    ${candidato.vaga_titulo}
                                </p>
                                <div class="flex flex-wrap gap-4 text-sm text-gray-600">
                                    <span class="flex items-center gap-1"><span>📧</span> ${candidato.email}</span>
                                    ${candidato.telefone ? `<span class="flex items-center gap-1"><span>📱</span> ${candidato.telefone}</span>` : ''}
                                    ${candidato.linkedin ? `<a href="${candidato.linkedin}" target="_blank" class="flex items-center gap-1 text-blue-600 hover:text-blue-800"><span>🔗</span> LinkedIn</a>` : ''}
                                </div>
                                <p class="text-xs text-gray-500 mt-2">Favoritado em: ${dataFavorito}</p>
                            </div>
                        </div>
                    </div>
                    <div class="flex flex-col items-center gap-4 lg:w-48">
                        <div class="flex gap-3">
                            ${candidato.vaga_titulo !== 'Favorito Geral' ?
                                `<div class="text-center bg-gradient-to-r from-blue-500 to-indigo-500 text-white px-4 py-3 rounded-xl shadow-md">
                                    <div class="text-lg font-bold">${candidato.posicao}º</div>
                                    <div class="text-xs opacity-90">posição</div>
                                </div>
                                <div class="text-center bg-gradient-to-r from-green-500 to-emerald-500 text-white px-4 py-3 rounded-xl shadow-md">
                                    <div class="text-lg font-bold">${candidato.score}%</div>
                                    <div class="text-xs opacity-90">match</div>
                                </div>` :
                                `<div class="text-center bg-gradient-to-r from-yellow-500 to-orange-500 text-white px-4 py-3 rounded-xl shadow-md">
                                    <div class="text-lg font-bold">⭐</div>
                                    <div class="text-xs opacity-90">geral</div>
                                </div>`
                            }
                        </div>
                        <div class="flex gap-2">
                            <button onclick="toggleFavoriteCandidate(${candidato.id}, ${candidato.vaga_id}, this)"
                                    class="text-2xl favorite-btn transition duration-200 hover:scale-125"
                                    data-favorited="true"
                                    title="Clique para remover dos favoritos">
                                ⭐
                            </button>
                            ${candidato.vaga_id > 0 ? `<button onclick="encerrarVagaDireta(this, ${candidato.vaga_id})"
                                class="bg-gradient-to-r from-orange-500 to-red-500 hover:from-orange-600 hover:to-red-600 text-white px-3 py-1 rounded-lg text-sm font-semibold transition-all duration-300 transform hover:scale-105">
                                🔒 Encerrar Vaga
                            </button>` : ''}
                        </div>
                    </div>
                </div>
            </div>
        `;
    });
    html += '</div>';
    container.innerHTML = html;
}

// Alterna favorito
async function toggleFavoriteCandidate(candidatoId, vagaId, button) {
    const isFavorited = button.getAttribute('data-favorited') === 'true';
    const apiUrl = vagaId === 0 ? '/api/favoritar-candidato-geral' : '/api/favoritar-candidato';
    const payload = { candidato_id: candidatoId, acao: isFavorited ? 'remove' : 'add' };
    if (vagaId !== 0) payload.vaga_id = vagaId;

    try {
        button.classList.add('opacity-50', 'pointer-events-none');

        const response = await fetch(apiUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const result = await response.json();
        if (result.success) {
            button.setAttribute('data-favorited', isFavorited ? 'false' : 'true');
            button.innerHTML = isFavorited ? '☆' : '⭐';

            if (isFavorited) {
                window.candidatosFavoritos = window.candidatosFavoritos.filter(c => !(c.id === candidatoId && c.vaga_id === vagaId));
                aplicarFiltros();
            } else {
                window.candidatosFavoritos.push({
                    id: candidatoId,
                    vaga_id: vagaId,
                    vaga_titulo: vagaId === 0 ? 'Favorito Geral' : 'Nova Vaga',
                    nome: 'Carregando...', // Será atualizado ao recarregar
                    email: '',
                    telefone: '',
                    linkedin: '',
                    score: 0,
                    posicao: 0,
                    data_favorito: new Date().toISOString()
                });
                aplicarFiltros();
            }

            updateStats();
            showToast(isFavorited ? 'Removido dos favoritos' : 'Adicionado aos favoritos', 'success');
        } else {
            showToast(result.message || 'Erro ao atualizar favorito', 'error');
        }
    } catch (error) {
        console.error('Erro ao atualizar favorito:', error);
        showToast('Erro ao atualizar favorito', 'error');
    } finally {
        button.classList.remove('opacity-50', 'pointer-events-none');
    }
}

// Encerrar vaga direto
async function encerrarVagaDireta(button, vagaId) {
    if (!confirm('Deseja encerrar esta vaga?')) return;

    try {
        button.disabled = true;
        button.classList.add('opacity-50');
        const response = await fetch(`/api/vagas/${vagaId}/encerrar`, { method: 'POST' });
        const result = await response.json();

        if (result.success) {
            showToast('Vaga encerrada com sucesso!', 'success');
            button.textContent = 'Encerrada';
            button.classList.remove('hover:from-orange-600', 'hover:to-red-600');
            button.classList.add('bg-gray-400', 'cursor-not-allowed');
        } else {
            showToast(result.message || 'Erro ao encerrar a vaga.', 'error');
            button.disabled = false;
        }
    } catch (error) {
        console.error('Erro ao encerrar vaga:', error);
        showToast('Erro ao encerrar vaga.', 'error');
        button.disabled = false;
    }
}

// Limpar filtros
function limparFiltros() {
    const searchInput = document.getElementById('searchInput');
    const vagaFilter = document.getElementById('vagaFilter');
    if (searchInput) searchInput.value = '';
    if (vagaFilter) vagaFilter.value = '';
    window.candidatosFiltrados = [...window.candidatosFavoritos];
    renderCandidatos();
}

// Toast
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `fixed bottom-4 right-4 z-50 px-6 py-4 rounded-xl shadow-lg transform translate-y-full transition-all duration-300 ${
        type === 'success' ? 'bg-green-500 text-white' :
        type === 'error' ? 'bg-yellow-500 text-white' :
        'bg-blue-500 text-white'
    }`;
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(() => { toast.classList.remove('translate-y-full'); }, 100);
    setTimeout(() => {
        toast.classList.add('translate-y-full');
        setTimeout(() => { document.body.removeChild(toast); }, 300);
    }, 3000);
}

// Eventos
document.addEventListener('DOMContentLoaded', () => {
    const searchInput = document.getElementById('searchInput');
    if (searchInput) searchInput.addEventListener('input', aplicarFiltros);

    loadCandidatosFavoritos();
});
