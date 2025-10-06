
// ============================
// Gerenciamento de seções do dashboard
// ============================

let notificacoesCache = [];
let categoriasBusca = [];
let localizacoesBusca = [];
let notificacoesInterval = null;
let ultimaAtualizacao = null;

function showSection(sectionName, event) {
    // Esconder todas as seções
    document.querySelectorAll('.content-section').forEach(section => {
        section.classList.add('hidden');
    });

    // Mostrar seção selecionada
    const targetSection = document.getElementById(`section-${sectionName}`);
    if (targetSection) {
        targetSection.classList.remove('hidden');
    }

    // Atualizar botões de filtro
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.classList.remove('filter-active');
        btn.classList.add('bg-gray-100', 'text-gray-700');
        btn.style.background = '';
        btn.style.color = '';
        btn.style.transform = '';
        btn.style.boxShadow = '';
    });

    // Aplicar estilo ativo no botão clicado
    if (event && event.target) {
        const activeBtn = event.target;
        activeBtn.classList.add('filter-active');
        activeBtn.classList.remove('bg-gray-100', 'text-gray-700');
        activeBtn.style.background = 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)';
        activeBtn.style.color = 'white';
        activeBtn.style.transform = 'translateY(-2px)';
        activeBtn.style.boxShadow = '0 4px 12px rgba(102, 126, 234, 0.4)';
    }

    // Carregar conteúdo específico se necessário
    if (sectionName === 'todas') {
        loadAllJobs();
        loadSearchFilters();
    } else if (sectionName === 'assistente-ia') {
        inicializarAssistenteIA();
    }
}

// Carregar todas as vagas
async function loadAllJobs() {
    const container = document.getElementById('todasVagasContainer');

    try {
        const response = await fetch('/api/todas-vagas');
        const vagas = await response.json();

        if (vagas.length === 0) {
            container.innerHTML = `
                <div class="text-center py-12 bg-white rounded-2xl shadow-sm border border-gray-100">
                    <div class="w-24 h-24 bg-gray-100 rounded-full mx-auto mb-6 flex items-center justify-center">
                        <span class="text-4xl">🔍</span>
                    </div>
                    <h3 class="text-xl font-bold text-gray-600 mb-3">Nenhuma vaga disponível</h3>
                    <p class="text-gray-500">No momento não há vagas ativas no sistema.</p>
                </div>
            `;
            return;
        }

        renderVagas(vagas, container);
    } catch (error) {
        console.error('Erro ao carregar vagas:', error);
        container.innerHTML = `
            <div class="text-center py-12 bg-white rounded-2xl shadow-sm border border-gray-100">
                <div class="w-24 h-24 bg-red-100 rounded-full mx-auto mb-6 flex items-center justify-center">
                    <span class="text-4xl">❌</span>
                </div>
                <h3 class="text-xl font-bold text-gray-600 mb-3">Erro ao carregar vagas</h3>
                <p class="text-gray-500">Tente novamente mais tarde.</p>
            </div>
        `;
    }
}

// Realizar busca avançada
async function realizarBusca() {
    const filtros = {
        keyword: document.getElementById('searchKeyword').value,
        location: document.getElementById('searchLocation').value,
        category: document.getElementById('searchCategory').value,
        urgency: document.getElementById('searchUrgency').value,
        salary: document.getElementById('searchSalary').value,
        type: document.getElementById('searchType').value
    };

    const container = document.getElementById('todasVagasContainer');
    container.innerHTML = `
        <div class="text-center py-8">
            <div class="animate-spin w-8 h-8 border-4 border-purple-500 border-t-transparent rounded-full mx-auto mb-4"></div>
            <p class="text-gray-500">Buscando vagas...</p>
        </div>
    `;

    try {
        const queryParams = new URLSearchParams();
        Object.keys(filtros).forEach(key => {
            if (filtros[key]) {
                queryParams.append(key, filtros[key]);
            }
        });

        const response = await fetch(`/api/buscar-vagas?${queryParams}`);
        const vagas = await response.json();

        if (vagas.length === 0) {
            container.innerHTML = `
                <div class="text-center py-12 bg-white rounded-2xl shadow-sm border border-gray-100">
                    <div class="w-24 h-24 bg-gray-100 rounded-full mx-auto mb-6 flex items-center justify-center">
                        <span class="text-4xl">😔</span>
                    </div>
                    <h3 class="text-xl font-bold text-gray-600 mb-3">Nenhuma vaga encontrada</h3>
                    <p class="text-gray-500">Tente ajustar os filtros de busca.</p>
                </div>
            `;
            return;
        }

        renderVagas(vagas, container, `${vagas.length} vaga(s) encontrada(s)`);
    } catch (error) {
        console.error('Erro na busca:', error);
        container.innerHTML = `
            <div class="text-center py-12 bg-white rounded-2xl shadow-sm border border-gray-100">
                <div class="w-24 h-24 bg-red-100 rounded-full mx-auto mb-6 flex items-center justify-center">
                    <span class="text-4xl">❌</span>
                </div>
                <h3 class="text-xl font-bold text-gray-600 mb-3">Erro na busca</h3>
                <p class="text-gray-500">Tente novamente mais tarde.</p>
            </div>
        `;
    }
}

// Renderizar vagas
function renderVagas(vagas, container, titulo = null) {
    let html = '';

    if (titulo) {
        html += `
            <div class="mb-6">
                <h3 class="text-xl font-bold text-gray-800 mb-2">Resultados</h3>
                <p class="text-gray-600">${titulo}</p>
            </div>
        `;
    }

    html += '<div class="grid gap-6">';

    vagas.forEach(vaga => {
        html += `
            <div class="bg-white rounded-2xl p-6 shadow-sm border border-gray-100 hover:shadow-xl hover:border-purple-200 transition-all duration-300 transform hover:-translate-y-1 group">
                <div class="flex flex-col lg:flex-row lg:items-start justify-between gap-4">
                    <div class="flex-1">
                        <div class="flex items-center gap-3 mb-3">
                            <h3 class="text-xl font-bold text-gray-800 group-hover:text-purple-600 transition-colors">
                                ${vaga.titulo}
                            </h3>
                            ${vaga.is_favorita ? '<span class="bg-red-100 text-red-800 px-2 py-1 rounded-full text-xs font-medium">❤️ Favorita</span>' : ''}
                        </div>

                        <div class="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm text-gray-600 mb-4">
                            <div class="flex items-center gap-2">
                                <span>🏢</span>
                                <span>${vaga.empresa_nome}</span>
                            </div>
                            <div class="flex items-center gap-2">
                                <span>💰</span>
                                <span class="font-semibold text-green-600">R$ ${vaga.salario_oferecido.toLocaleString('pt-BR', {minimumFractionDigits: 2})}</span>
                            </div>
                            <div class="flex items-center gap-2">
                                <span>🏠</span>
                                <span>${vaga.tipo_vaga || 'Presencial'}</span>
                            </div>
                            ${vaga.endereco_vaga ? `
                            <div class="flex items-center gap-2">
                                <span>📍</span>
                                <span>${vaga.endereco_vaga}</span>
                            </div>` : ''}
                        </div>

                        <p class="text-gray-600 line-clamp-2 mb-3">${vaga.descricao}</p>

                        ${vaga.diferenciais ? `
                        <div class="bg-blue-50 border border-blue-200 rounded-lg p-3 mb-3">
                            <div class="flex items-center gap-2 mb-2">
                                <span class="text-blue-600">⭐</span>
                                <span class="text-sm font-medium text-blue-800">Diferenciais:</span>
                            </div>
                            <p class="text-sm text-blue-700">${vaga.diferenciais}</p>
                        </div>` : ''}
                    </div>

                    <div class="flex flex-col items-center gap-3 lg:w-32">
                        <div class="text-center bg-gradient-to-r from-purple-500 to-blue-500 text-white px-4 py-3 rounded-xl shadow-md">
                            <div class="text-lg font-bold">${vaga.score.toFixed(0)}%</div>
                            <div class="text-xs opacity-90">match</div>
                        </div>

                        <div class="flex gap-2">
                            <button onclick="toggleFavorite(${vaga.id}, this)" 
                                    data-favorited="${vaga.is_favorita}" 
                                    class="favorite-btn text-xl transition-all duration-300 hover:scale-125 ${vaga.is_favorita ? 'text-red-500' : 'text-gray-300'}">
                                ${vaga.is_favorita ? '❤️' : '🤍'}
                            </button>
                        </div>
                    </div>
                </div>

                <div class="flex gap-3 pt-4 border-t border-gray-100">
                    <a href="/vaga/${vaga.id}" 
                       class="bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded-xl font-semibold transition-all duration-300 transform hover:scale-105 flex items-center gap-2">
                        <span>👁️</span>
                        Ver Detalhes
                    </a>

                    ${!vaga.ja_candidatou ? 
                        `<a href="/candidatar/${vaga.id}" class="group/btn bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 text-white font-bold px-6 py-3 rounded-xl shadow-lg transition-all duration-300 transform hover:scale-105 hover:shadow-xl flex items-center gap-2">
                            <span class="transition-transform group-hover/btn:translate-x-1">🚀</span>
                            Candidatar-se
                        </a>` : 
                        '<span class="bg-gray-100 text-gray-600 px-4 py-2 rounded-xl text-sm">✅ Já candidatado</span>'
                    }
                </div>
            </div>
        `;
    });

    html += '</div>';
    container.innerHTML = html;
}

// Limpar filtros de busca
function limparFiltros() {
    document.getElementById('searchKeyword').value = '';
    document.getElementById('searchLocation').value = '';
    document.getElementById('searchCategory').value = '';
    document.getElementById('searchUrgency').value = '';
    document.getElementById('searchSalary').value = '';
    document.getElementById('searchType').value = '';
    loadAllJobs();
}

