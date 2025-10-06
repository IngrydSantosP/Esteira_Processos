async function mostrarDetalhesScore(candidatoId, candidatoNome, scoreTotal) {
    try {
        // Buscar detalhes do score via API
        const response = await fetch(`/api/score-detalhes/${candidatoId}/{{ vaga_id }}`);
        const detalhes = await response.json();
        
        if (detalhes.error) {
            showToast('Erro ao carregar detalhes do score', 'error');
            return;
        }
        
        // Preencher o modal
        const conteudo = document.getElementById('conteudoScore');
        conteudo.innerHTML = `  
            <div class="text-center mb-6">
                <h4 class="text-xl font-bold text-gray-800 mb-2">${candidatoNome}</h4>
                <div class="text-3xl font-bold text-green-600">${Math.round(scoreTotal)}% de Match</div>
            </div>
            
            <div class="space-y-4">
                <div class="bg-purple-50 rounded-lg p-4">
                    <div class="flex justify-between items-center mb-2">
                        <h5 class="font-semibold text-purple-800">💰 Compatibilidade Salarial</h5>
                        <span class="text-purple-600 font-bold">${detalhes.salarial || 0}pts (20%)</span>
                    </div>
                    <p class="text-sm text-gray-600">${detalhes.explicacao_salarial || 'Análise da pretensão vs. salário oferecido'}</p>
                </div>
                
                <div class="bg-blue-50 rounded-lg p-4">
                    <div class="flex justify-between items-center mb-2">
                        <h5 class="font-semibold text-blue-800">⚡ Requisitos Técnicos</h5>
                        <span class="text-blue-600 font-bold">${detalhes.requisitos || 0}pts (40%)</span>
                    </div>
                    <p class="text-sm text-gray-600">${detalhes.explicacao_requisitos || 'Compatibilidade com tecnologias e habilidades'}</p>
                </div>
                
                <div class="bg-green-50 rounded-lg p-4">
                    <div class="flex justify-between items-center mb-2">
                        <h5 class="font-semibold text-green-800">🎓 Experiência</h5>
                        <span class="text-green-600 font-bold">${detalhes.experiencia || 0}pts (15%)</span>
                    </div>
                    <p class="text-sm text-gray-600">${detalhes.explicacao_experiencia || 'Nível de senioridade identificado'}</p>
                </div>
                
                <div class="bg-yellow-50 rounded-lg p-4">
                    <div class="flex justify-between items-center mb-2">
                        <h5 class="font-semibold text-yellow-800">⭐ Diferenciais</h5>
                        <span class="text-yellow-600 font-bold">${detalhes.diferenciais || 0}pts (10%)</span>
                    </div>
                    <p class="text-sm text-gray-600">${detalhes.explicacao_diferenciais || 'Certificações e habilidades extras'}</p>
                </div>
                
                <div class="bg-orange-50 rounded-lg p-4">
                    <div class="flex justify-between items-center mb-2">
                        <h5 class="font-semibold text-orange-800">📍 Localização</h5>
                        <span class="text-orange-600 font-bold">${detalhes.localizacao || 0}pts (10%)</span>
                    </div>
                    <p class="text-sm text-gray-600">${detalhes.explicacao_localizacao || 'Proximidade geográfica'}</p>
                </div>
                
                <div class="bg-indigo-50 rounded-lg p-4">
                    <div class="flex justify-between items-center mb-2">
                        <h5 class="font-semibold text-indigo-800">🎓 Formação</h5>
                        <span class="text-indigo-600 font-bold">${detalhes.formacao || 0}pts (5%)</span>
                    </div>
                    <p class="text-sm text-gray-600">${detalhes.explicacao_formacao || 'Nível educacional'}</p>
                </div>
            </div>
        `;
        
        // Mostrar modal
        document.getElementById('modalScore').classList.remove('hidden');
        
    } catch (error) {
        console.error('Erro ao carregar detalhes do score:', error);
        showToast('Erro ao carregar detalhes do score', 'error');
    }
}

function fecharModalScore() {
    document.getElementById('modalScore').classList.add('hidden');
}




// Favoritar/desfavoritar candidato
function toggleFavoriteCandidato(candidatoId, vagaId, btn) {
    const favorited = btn.getAttribute('data-favorited') === 'true';

    fetch('/api/favoritar-candidato', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            candidato_id: candidatoId,
            vaga_id: vagaId,
            acao: favorited ? 'remove' : 'add'
        })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            btn.setAttribute('data-favorited', !favorited);
            const text = btn.querySelector('.favorite-text');
            const icon = btn.querySelector('.favorite-icon');

            if (!favorited) {
                text.textContent = 'Favorito';
                btn.classList.add('bg-yellow-600', 'text-white');
                btn.classList.remove('bg-yellow-100', 'text-yellow-700');
            } else {
                text.textContent = 'Favoritar';
                btn.classList.remove('bg-yellow-600', 'text-white');
                btn.classList.add('bg-yellow-100', 'text-yellow-700');
            }
        } else {
            alert(data.message);
        }
    })
    .catch(err => console.error('Erro ao favoritar candidato:', err));
}

// Modal de score
function mostrarDetalhesScore(candidatoId, nome, score) {
    const modal = document.getElementById('modalScore');
    const conteudo = document.getElementById('conteudoScore');
    conteudo.innerHTML = `<p><strong>${nome}</strong> tem um score de <strong>${score}%</strong>.</p>`;
    modal.classList.remove('hidden');
}

function fecharModalScore() {
    document.getElementById('modalScore').classList.add('hidden');
}

// Funções de filtros
function aplicarFiltros() { console.log('Filtros aplicados'); }
function limparFiltros() { console.log('Filtros limpos'); }
function toggleFavoritosOnly() { console.log('Toggle favoritos'); }
