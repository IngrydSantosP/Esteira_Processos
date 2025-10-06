let chart;

function atualizarValor(categoria, valor) {
    document.getElementById(`valor-${categoria}`).textContent = valor + '%';
    calcularTotal();
    atualizarChart();
}

function calcularTotal() {
    const categorias = ['salarial', 'requisitos', 'experiencia', 'diferenciais', 'localizacao', 'formacao'];
    let total = 0;
    
    categorias.forEach(cat => {
        total += parseInt(document.getElementById(`peso-${cat}`).value);
    });
    
    document.getElementById('total-pesos').textContent = total;
    
    const alerta = document.getElementById('alerta-soma');
    if (total !== 100) {
        alerta.style.display = 'block';
    } else {
        alerta.style.display = 'none';
    }
}

function atualizarChart() {
    const data = {
        labels: ['Salarial', 'Requisitos', 'Experiência', 'Diferenciais', 'Localização', 'Formação'],
        datasets: [{
            data: [
                document.getElementById('peso-salarial').value,
                document.getElementById('peso-requisitos').value,
                document.getElementById('peso-experiencia').value,
                document.getElementById('peso-diferenciais').value,
                document.getElementById('peso-localizacao').value,
                document.getElementById('peso-formacao').value
            ],
            backgroundColor: [
                '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF', '#FF9F40'
            ]
        }]
    };
    
    if (chart) {
        chart.data = data;
        chart.update();
    } else {
        const ctx = document.getElementById('chart-pesos').getContext('2d');
        chart = new Chart(ctx, {
            type: 'radar',
            data: data,
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    r: {
                        beginAtZero: true,
                        max: 100
                    }
                }
            }
        });
    }
}

function aplicarTemplate(templateId) {
    fetch('/score/aplicar-template-score', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({template_id: templateId})
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Atualizar sliders com os valores do template
            Object.keys(data.pesos).forEach(categoria => {
                const slider = document.getElementById(`peso-${categoria}`);
                slider.value = data.pesos[categoria];
                atualizarValor(categoria, data.pesos[categoria]);
            });
            alert('Template aplicado com sucesso!');
        } else {
            alert('Erro: ' + data.error);
        }
    });
}

function resetarPadrao() {
    const padrao = {
        'salarial': 20,
        'requisitos': 40,
        'experiencia': 15,
        'diferenciais': 10,
        'localizacao': 10,
        'formacao': 5
    };
    
    Object.keys(padrao).forEach(categoria => {
        const slider = document.getElementById(`peso-${categoria}`);
        slider.value = padrao[categoria];
        atualizarValor(categoria, padrao[categoria]);
    });
}

document.getElementById('form-configuracao-score').addEventListener('submit', function(e) {
    e.preventDefault();
    
    const total = parseInt(document.getElementById('total-pesos').textContent);
    if (total !== 100) {
        alert('A soma dos pesos deve ser exatamente 100%');
        return;
    }
    
    const pesos = {
        'salarial': document.getElementById('peso-salarial').value,
        'requisitos': document.getElementById('peso-requisitos').value,
        'experiencia': document.getElementById('peso-experiencia').value,
        'diferenciais': document.getElementById('peso-diferenciais').value,
        'localizacao': document.getElementById('peso-localizacao').value,
        'formacao': document.getElementById('peso-formacao').value
    };
    
    fetch('/score/salvar-configuracao-score', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({pesos: pesos})
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('Configuração salva com sucesso!');
        } else {
            alert('Erro: ' + data.error);
        }
    });
});

// Inicializar chart ao carregar a página
window.onload = function() {
    atualizarChart();
};