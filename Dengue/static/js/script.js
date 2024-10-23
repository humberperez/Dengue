

var ctx = document.getElementById('myChart');
var myChart = new Chart(ctx, {
    type: 'pie',
    data: {
        labels: JSON.parse(document.getElementById('labels').textContent),
        datasets: [{
            label: 'Grupo de Riesgo',
            data: JSON.parse(document.getElementById('values').textContent),
            backgroundColor: [
                'green',
                'yellow',
                'red'
            ],
            borderColor: [
                'green',
                'yellow',
                'red'
            ],
            borderWidth: 1
        }]
    },
   
    options: {
        scales: {
            y: {
                beginAtZero: true
            }
        }
    }
});