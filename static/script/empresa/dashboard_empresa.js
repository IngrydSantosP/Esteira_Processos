// Toggle para a Busca Avançada
function toggleAdvancedSearch() {
  const panel = document.getElementById('advancedSearchPanel');
  panel.classList.toggle('hidden');

  const searchIcon = document.getElementById('searchIcon');
  searchIcon.classList.toggle('rotate-12');
}

// Realizar busca de vagas
function realizarBuscaVagas() {
  const keyword = document.getElementById('searchKeyword').value.toLowerCase();
  const status = document.getElementById('searchStatus').value;
  const urgency = document.getElementById('searchUrgency').value;
  const candidatos = document.getElementById('searchCandidatos').value;

  const cards = document.querySelectorAll('.vaga-card');
  let visibleCount = 0;

  cards.forEach(card => {
    let shouldShow = true;

    // Filtro por palavra-chave
    if (keyword) {
      const titulo = card.querySelector('h3')?.textContent.toLowerCase() || '';
      const descricao = card.querySelector('.vaga-descricao')?.textContent.toLowerCase() || '';
      if (!titulo.includes(keyword) && !descricao.includes(keyword)) {
        shouldShow = false;
      }
    }

    // Filtro por status
    if (status && card.getAttribute('data-status') !== status) {
      shouldShow = false;
    }

    // Filtro por urgência
    if (urgency) {
      const vagaUrgency = card.getAttribute('data-urgencia');
      if (vagaUrgency !== urgency) {
        shouldShow = false;
      }
    }

    // Filtro por candidatos
    if (candidatos) {
      const totalCandidatos = parseInt(card.getAttribute('data-candidatos')) || 0;
      switch(candidatos) {
        case 'sem_candidatos':
          if (totalCandidatos > 0) shouldShow = false;
          break;
        case 'poucos_candidatos':
          if (totalCandidatos === 0 || totalCandidatos > 5) shouldShow = false;
          break;
        case 'muitos_candidatos':
          if (totalCandidatos <= 5) shouldShow = false;
          break;
      }
    }

    card.style.display = shouldShow ? 'block' : 'none';
    if (shouldShow) visibleCount++;
  });

  showToast(`${visibleCount} vaga(s) encontrada(s)`, 'success');
}

// Limpar filtros de busca
function limparFiltrosBusca() {
  ['searchKeyword', 'searchStatus', 'searchUrgency', 'searchCandidatos'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.value = '';
  });

  document.querySelectorAll('.vaga-card').forEach(card => {
    card.style.display = 'block';
  });

  showToast('Filtros limpos', 'info');
}

// Filtrar vagas por status (ex: 'todas', 'ativa', 'encerrada', etc)
function filtrarVagas(status) {
  const cards = document.querySelectorAll('.vaga-card');
  let visibleCount = 0;

  cards.forEach(card => {
    const cardStatus = card.getAttribute('data-status');
    const mostrar = status === 'todas' || cardStatus === status;
    card.style.display = mostrar ? 'block' : 'none';
    if (mostrar) visibleCount++;
  });

  // Atualiza classes dos botões para refletir filtro ativo
  document.querySelectorAll('.filter-btn').forEach(btn => {
    btn.classList.remove('filter-active');
    btn.classList.add('bg-gray-100', 'text-gray-700');
  });

  const activeBtn = document.querySelector(`.filter-btn[onclick="filtrarVagas('${status}')"]`);
  if (activeBtn) {
    activeBtn.classList.remove('bg-gray-100', 'text-gray-700');
    activeBtn.classList.add('filter-active');
  }

  showToast(`${visibleCount} vaga(s) encontrada(s)`, 'info');
}

// Cria um announcer para acessibilidade (ex: leitura por screen readers)
function createAnnouncer() {
  const announcer = document.createElement('div');
  announcer.id = 'filter-announcer';
  announcer.setAttribute('aria-live', 'polite');
  announcer.setAttribute('aria-atomic', 'true');
  Object.assign(announcer.style, {
    position: 'absolute',
    left: '-10000px',
    width: '1px',
    height: '1px',
    overflow: 'hidden'
  });
  document.body.appendChild(announcer);
  return announcer;
}

// Navegação por teclado entre botões de filtro
document.addEventListener('DOMContentLoaded', () => {
  const filterButtons = document.querySelectorAll('.filter-btn');

  filterButtons.forEach((btn, index) => {
    btn.addEventListener('keydown', e => {
      switch(e.key) {
        case 'ArrowLeft':
        case 'ArrowUp':
          e.preventDefault();
          filterButtons[(index - 1 + filterButtons.length) % filterButtons.length].focus();
          break;
        case 'ArrowRight':
        case 'ArrowDown':
          e.preventDefault();
          filterButtons[(index + 1) % filterButtons.length].focus();
          break;
        case 'Enter':
        case ' ':
          e.preventDefault();
          btn.click();
          break;
      }
    });
  });
});

// Função para reativar vaga
async function reativarVaga(vagaId) {
  if (!confirm('Tem certeza que deseja reativar esta vaga?')) {
    return;
  }

  try {
    const response = await fetch('/encerrar_vaga', {  // Verifique se a URL está correta no backend!
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        vaga_id: vagaId,
        acao: 'reativar'
      })
    });

    if (!response.ok) {
      // Resposta com status diferente de 2xx
      const text = await response.text();
      console.error('Erro na resposta do servidor:', text);
      showToast('Erro ao reativar vaga. Tente novamente.', 'error');
      return;
    }

    // Tenta ler JSON, pode lançar erro se resposta não for JSON válido
    const result = await response.json();

    if (result.success) {
      showToast('Vaga reativada com sucesso!', 'success');
      setTimeout(() => location.reload(), 1000);
    } else {
      showToast('Erro ao reativar vaga: ' + (result.error || 'Erro desconhecido'), 'error');
    }

  } catch (error) {
    console.error('Erro ao reativar vaga:', error);
    showToast('Erro ao reativar vaga. Tente novamente.', 'error');
  }
}

// Sistema de favoritos com auto-reload
async function toggleFavoriteCandidate(candidatoId, vagaId, button) {
  const isFavorited = button.dataset.favorited === 'true';

  try {
    button.classList.add('animate-pulse');

    const response = await fetch('/api/favoritar-candidato', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        candidato_id: candidatoId,
        vaga_id: vagaId,
        acao: 'toggle'
      })
    });

    if (!response.ok) {
      const text = await response.text();
      console.error('Erro na resposta do servidor:', text);
      showToast('Erro ao favoritar candidato', 'error');
      return;
    }

    const result = await response.json();

    if (result.success) {
      button.dataset.favorited = result.favorited;
      button.textContent = result.favorited ? '❤️' : '🤍';
      button.className = `favorite-btn text-xl transition-all duration-300 hover:scale-125 ${
        result.favorited ? 'text-red-500' : 'text-gray-300'
      }`;

      showToast(result.message, 'success');

      // Reload imediato para refletir mudanças
      location.reload();
    } else {
      showToast(result.message || 'Erro ao favoritar candidato', 'error');
    }

  } catch (error) {
    console.error('Erro ao favoritar:', error);
    showToast('Erro ao favoritar candidato', 'error');
  } finally {
    button.classList.remove('animate-pulse');
  }
}

// Toast notifications
function showToast(message, type = 'info') {
  const toast = document.createElement('div');
  toast.className = `fixed bottom-4 right-4 z-50 px-6 py-4 rounded-xl shadow-lg transform translate-y-full transition-all duration-300 ${
    type === 'success' ? 'bg-green-500 text-white' :
    type === 'error' ? 'bg-red-500 text-white' :
    'bg-blue-500 text-white'
  }`;
  toast.textContent = message;

  document.body.appendChild(toast);

  // Aparece
  setTimeout(() => {
    toast.classList.remove('translate-y-full');
  }, 100);

  // Desaparece
  setTimeout(() => {
    toast.classList.add('translate-y-full');
    setTimeout(() => {
      toast.remove();
    }, 300);
  }, 3000);
}

window.toggleAdvancedSearch = toggleAdvancedSearch;
window.realizarBuscaVagas = realizarBuscaVagas;
window.limparFiltrosBusca = limparFiltrosBusca;
window.filtrarVagas = filtrarVagas;
window.reativarVaga = reativarVaga;
window.toggleFavoriteCandidate = toggleFavoriteCandidate;