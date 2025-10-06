// static/script/empresa/relatorio.js

let dadosGraficos;
let graficoPizza, graficoBarras, graficoLinha;

// Essa função será chamada para inicializar o código com os dados que vêm do backend
function inicializarRelatorio(dados) {
  dadosGraficos = dados;
  carregarMetricas();
  criarGraficos();
  gerarInsights();
}

function carregarMetricas() {
  const metricas = document.getElementById('metricas');
  metricas.innerHTML = `
      <div class="metric-cards-container">
          <div class="bg-gradient-to-br from-blue-500 to-blue-600 text-white p-6 rounded-lg metric-card">
              <h3 class="text-3xl font-bold">${dadosGraficos && dadosGraficos.pizza && dadosGraficos.pizza.data ? dadosGraficos.pizza.data.reduce((a, b) => a + b, 0) : 0}</h3>
              <p class="opacity-90">Total de Candidaturas</p>
          </div>
          <div class="bg-gradient-to-br from-green-500 to-green-600 text-white p-6 rounded-lg metric-card">
              <h3 class="text-3xl font-bold">${dadosGraficos && dadosGraficos.pizza && dadosGraficos.pizza.labels ? dadosGraficos.pizza.labels.length : 0}</h3>
              <p class="opacity-90">Vagas Ativas</p>
          </div>
          <div class="bg-gradient-to-br from-purple-500 to-purple-600 text-white p-6 rounded-lg metric-card">
              <h3 class="text-3xl font-bold">${dadosGraficos && dadosGraficos.barras && dadosGraficos.barras.data && dadosGraficos.barras.data.length > 0 ? (dadosGraficos.barras.data.reduce((a, b) => a + b, 0) / dadosGraficos.barras.data.length).toFixed(1) : 0}%</h3>
              <p class="opacity-90">Score Médio Geral</p>
          </div>
          <div class="bg-gradient-to-br from-orange-500 to-orange-600 text-white p-6 rounded-lg metric-card">
              <h3 class="text-3xl font-bold">${dadosGraficos && dadosGraficos.linha && dadosGraficos.linha.data ? dadosGraficos.linha.data.reduce((a, b) => a + b, 0) : 0}</h3>
              <p class="opacity-90">Candidaturas (30 dias)</p>
          </div>
      </div>
  `;
}

function criarGraficos() {
  const ctxPizza = document.getElementById('grafico-pizza').getContext('2d');
  graficoPizza = new Chart(ctxPizza, {
      type: 'pie',
      data: {
          labels: dadosGraficos && dadosGraficos.pizza ? dadosGraficos.pizza.labels : [],
          datasets: [{
              data: dadosGraficos && dadosGraficos.pizza ? dadosGraficos.pizza.data : [],
              backgroundColor: [
                  '#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6',
                  '#06B6D4', '#84CC16', '#F97316', '#EC4899', '#6B7280'
              ]
          }]
      },
      options: {
          responsive: true,
          plugins: {
              legend: {
                  position: 'bottom'
              }
          }
      }
  });

  const ctxBarras = document.getElementById('grafico-barras').getContext('2d');
  graficoBarras = new Chart(ctxBarras, {
      type: 'bar',
      data: {
          labels: dadosGraficos && dadosGraficos.barras ? dadosGraficos.barras.labels : [],
          datasets: [{
              label: 'Score Médio (%)',
              data: dadosGraficos && dadosGraficos.barras ? dadosGraficos.barras.data : [],
              backgroundColor: '#3B82F6',
              borderColor: '#1D4ED8',
              borderWidth: 1
          }]
      },
      options: {
          responsive: true,
          scales: {
              y: {
                  beginAtZero: true,
                  max: 100
              }
          }
      }
  });

  const ctxLinha = document.getElementById('grafico-linha').getContext('2d');
  graficoLinha = new Chart(ctxLinha, {
      type: 'line',
      data: {
          labels: dadosGraficos && dadosGraficos.linha ? dadosGraficos.linha.labels : [],
          datasets: [{
              label: 'Candidaturas por Dia',
              data: dadosGraficos && dadosGraficos.linha ? dadosGraficos.linha.data : [],
              borderColor: '#10B981',
              backgroundColor: 'rgba(16, 185, 129, 0.1)',
              tension: 0.4,
              fill: true
          }]
      },
      options: {
          responsive: true,
          scales: {
              y: {
                  beginAtZero: true
              }
          }
      }
  });
}

function gerarInsights() {
  const insights = document.getElementById('insights');
  let htmlInsights = '';

  if (dadosGraficos && dadosGraficos.pizza && dadosGraficos.pizza.data && dadosGraficos.pizza.data.length > 0) {
      const maxIndex = dadosGraficos.pizza.data.indexOf(Math.max(...dadosGraficos.pizza.data));
      htmlInsights += `
          <div class="bg-white p-4 rounded border-l-4 border-blue-500">
              <strong>🎯 Vaga Mais Popular:</strong> ${dadosGraficos.pizza.labels[maxIndex]}
              (${dadosGraficos.pizza.data[maxIndex]} candidatos)
          </div>
      `;
  }

  if (dadosGraficos && dadosGraficos.barras && dadosGraficos.barras.data && dadosGraficos.barras.data.length > 0) {
      const maxScoreIndex = dadosGraficos.barras.data.indexOf(Math.max(...dadosGraficos.barras.data));
      htmlInsights += `
          <div class="bg-white p-4 rounded border-l-4 border-green-500">
              <strong>⭐ Melhor Score:</strong> ${dadosGraficos.barras.labels[maxScoreIndex]}
              (${dadosGraficos.barras.data[maxScoreIndex]}% de compatibilidade média)
          </div>
      `;
  }

  if (dadosGraficos && dadosGraficos.linha && dadosGraficos.linha.data && dadosGraficos.linha.data.length >= 2) {
      const tendencia = dadosGraficos.linha.data[dadosGraficos.linha.data.length - 1] - dadosGraficos.linha.data[dadosGraficos.linha.data.length - 2];
      const cor = tendencia > 0 ? 'green' : tendencia < 0 ? 'red' : 'yellow';
      const emoji = tendencia > 0 ? '📈' : tendencia < 0 ? '📉' : '➡️';
      htmlInsights += `
          <div class="bg-white p-4 rounded border-l-4 border-${cor}-500">
              <strong>${emoji} Tendência:</strong>
              ${tendencia > 0 ? 'Aumento' : tendencia < 0 ? 'Diminuição' : 'Estabilidade'}
              nas candidaturas recentes
          </div>
      `;
  }

  insights.innerHTML = htmlInsights;
}

function aplicarFiltros() {
  const select = document.getElementById('filtroVagas');
  const vagasSelecionadas = Array.from(select.selectedOptions).map(option => option.value);

  fetch(`/api/relatorio/graficos?${vagasSelecionadas.map(v => `vagas=${v}`).join('&')}`)
      .then(response => response.json())
      .then(data => {
          dadosGraficos = data;
          atualizarGraficos();
          carregarMetricas();
          gerarInsights();
      })
      .catch(error => {
          console.error('Erro ao aplicar filtros:', error);
          alert('Erro ao aplicar filtros. Tente novamente.');
      });
}

function limparFiltros() {
  document.getElementById('filtroVagas').selectedIndex = -1;
  location.reload();
}

function atualizarGraficos() {
  graficoPizza.data.labels = (dadosGraficos && dadosGraficos.pizza) ? dadosGraficos.pizza.labels : [];
  graficoPizza.data.datasets[0].data = (dadosGraficos && dadosGraficos.pizza) ? dadosGraficos.pizza.data : [];
  graficoPizza.update();

  graficoBarras.data.labels = (dadosGraficos && dadosGraficos.barras) ? dadosGraficos.barras.labels : [];
  graficoBarras.data.datasets[0].data = (dadosGraficos && dadosGraficos.barras) ? dadosGraficos.barras.data : [];
  graficoBarras.update();

  graficoLinha.data.labels = (dadosGraficos && dadosGraficos.linha) ? dadosGraficos.linha.labels : [];
  graficoLinha.data.datasets[0].data = (dadosGraficos && dadosGraficos.linha) ? dadosGraficos.linha.data : [];
  graficoLinha.update();
}

function gerarRelatorioCompleto() {
  const select = document.getElementById('filtroVagas');
  const vagasSelecionadas = Array.from(select.selectedOptions).map(option => option.value);

  let url = '/empresa/relatorio/completo';
  if (vagasSelecionadas.length > 0) {
      url += '?' + vagasSelecionadas.map(v => `vagas=${v}`).join('&');
  }

  window.open(url, '_blank');
}
