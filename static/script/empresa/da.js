
  // Toggle para a Busca Avançada
  function toggleAdvancedSearch() {
    const panel = document.getElementById('advancedSearchPanel');
    const searchIcon = document.getElementById('searchIcon');
    
    // Alternar a classe hidden para manipular a visibilidade do painel
    panel.classList.toggle('hidden'); 

    // Alterna a rotação do ícone de busca
    searchIcon.classList.toggle('rotate-12');

    // Se o painel estiver visível, adicione a classe 'open' para a transição suave
    if (!panel.classList.contains('hidden')) {
        panel.classList.add('open');
    } else {
        panel.classList.remove('open');
    }
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
        const titulo = card.querySelector('h3').textContent.toLowerCase();
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

      if (shouldShow) {
        card.style.display = 'block';
        visibleCount++;
      } else {
        card.style.display = 'none';
      }
    });

    showToast(`${visibleCount} vaga(s) encontrada(s)`, 'success');
  }

  // Limpar filtros de busca
  function limparFiltrosBusca() {
    document.getElementById('searchKeyword').value = '';
    document.getElementById('searchStatus').value = '';
    document.getElementById('searchUrgency').value = '';
    document.getElementById('searchCandidatos').value = '';

    // Mostrar todas as vagas
    document.querySelectorAll('.vaga-card').forEach(card => {
      card.style.display = 'block';
    });

    showToast('Filtros limpos', 'info');
  }

    function filtrarVagas(status) {
      const cards = document.querySelectorAll('.vaga-card');
      let visibleCount = 0;

      cards.forEach(card => {
        const cardStatus = card.getAttribute('data-status');
        if (status === 'todas' || cardStatus === status) {
          card.style.display = 'block';
          visibleCount++;
        } else {
          card.style.display = 'none';
        }
      });

      // Atualizar botões com estilo similar ao dashboard candidato
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

    function createAnnouncer() {
      const announcer = document.createElement('div');
      announcer.id = 'filter-announcer';
      announcer.setAttribute('aria-live', 'polite');
      announcer.setAttribute('aria-atomic', 'true');
      announcer.style.position = 'absolute';
      announcer.style.left = '-10000px';
      announcer.style.width = '1px';
      announcer.style.height = '1px';
      announcer.style.overflow = 'hidden';
      document.body.appendChild(announcer);
      return announcer;
    }

    // Suporte a navegação por teclado nos filtros
    document.addEventListener('DOMContentLoaded', function() {
      const filterButtons = document.querySelectorAll('.filter-btn');

      filterButtons.forEach((btn, index) => {
        btn.addEventListener('keydown', function(e) {
          switch(e.key) {
            case 'ArrowLeft':
            case 'ArrowUp':
              e.preventDefault();
              const prevIndex = index > 0 ? index - 1 : filterButtons.length - 1;
              filterButtons[prevIndex].focus();
              break;
            case 'ArrowRight':
            case 'ArrowDown':
              e.preventDefault();
              const nextIndex = index < filterButtons.length - 1 ? index + 1 : 0;
              filterButtons[nextIndex].focus();
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

    document.addEventListener("DOMContentLoaded", function() {
      // Esconde todas as seções ao carregar a página
      const sections = document.querySelectorAll(".content-section");
      sections.forEach(section => section.classList.add("hidden"));

      // Mostra apenas a seção de "relatorios" por padrão e ativa o botão correspondente
      showSection("relatorios");
    });

  // Função para mostrar a seção clicada e ocultar as outras
  function showSection(sectionName, event = null) {
      // Esconde todas as seções
      const sections = document.querySelectorAll('.content-section');
      sections.forEach(section => section.classList.add('hidden'));

      // Mostra a seção clicada
      const targetSection = document.getElementById(`section-${sectionName}`);
      if (targetSection) targetSection.classList.remove('hidden');

      // Atualiza os botões de filtro
      const filterButtons = document.querySelectorAll('.filter-btn');
      filterButtons.forEach(btn => btn.classList.remove('filter-active'));

      // Marca o botão clicado como ativo
      const clickedBtn = event ? event.currentTarget : document.querySelector(`[onclick*="showSection('${sectionName}')"]`);
      if (clickedBtn) clickedBtn.classList.add('filter-active');
  }