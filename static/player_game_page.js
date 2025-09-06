// wait until the html document is fully loaded before running this code
document.addEventListener('DOMContentLoaded', function () {
    (function () {
      const section = document.getElementById('player-predict-section');
      if (!section) return;
  
      const playerId = section.dataset.playerId;
      const gameId = section.dataset.gameId;
      const playerName = section.dataset.playerName || 'Player';
  
      const btn = document.getElementById('player-predict-btn');
      const resultsBox = document.getElementById('player-predict-results');
      const errorBox = document.getElementById('player-predict-error');
      const loadingBox = document.getElementById('player-predict-loading');
      const matrixMount = document.getElementById('player-pred-matrix'); // 🔧 may be null
      const notesEl = document.getElementById('player-pred-notes');
  
      function show(el) { el && el.classList.remove('hidden'); }
      function hide(el) { el && el.classList.add('hidden'); }
  
      function resetOutputs() {
        hide(resultsBox);
        hide(errorBox);
        hide(loadingBox);
        if (matrixMount) { 
          matrixMount.innerHTML = '';
        }
        if (notesEl) hide(notesEl);
      }
  
      function renderPredictionMatrix(features) {
        const order = ['PTS', '3PM', 'REB', 'AST', 'TOV'];
        const maxRows = order.reduce((m, f) => Math.max(m, (features[f] || []).length), 0);
  
        const table = document.createElement('table');
        table.classList.add('prediction-table');
  
        const thead = document.createElement('thead');
        const hr = document.createElement('tr');
        order.forEach((name) => {
          const th = document.createElement('th');
          th.textContent = name;
          hr.appendChild(th);
        });
        thead.appendChild(hr);
        table.appendChild(thead);
  
        const tbody = document.createElement('tbody');
        for (let i = 0; i < maxRows; i++) {
          const tr = document.createElement('tr');
          order.forEach((name) => {
            const td = document.createElement('td');
            const arr = features[name] || [];
            const row = arr[i];
            if (row && typeof row.prob !== 'undefined' && row.prob !== 'No data') {
              td.textContent = `${row.condition} → ${row.prob}%`;
            } else if (row && row.prob === 'No data') {
              td.textContent = 'No data';
            } else {
              td.textContent = '';
            }
            tr.appendChild(td);
          });
          tbody.appendChild(tr);
        }
        table.appendChild(tbody);
        return table;
      }
  
      async function fetchPlayerPerformance() {
        btn.disabled = true;
        resetOutputs();
        show(loadingBox);
  
        try {
          const res = await fetch(`/api/player_predict/${encodeURIComponent(playerId)}/${encodeURIComponent(gameId)}`);
          if (!res.ok) throw new Error('Request failed');
          const data = await res.json();
  
          if (!data.features || Object.keys(data.features).length === 0) {
            throw new Error('No features in response');
          }
  
          const table = renderPredictionMatrix(data.features);
          if (matrixMount) { 
            matrixMount.appendChild(table);
          } else {
            console.warn('[player] Missing #player-pred-matrix mount point.');
          }
  
          hide(loadingBox);
          show(resultsBox);
          show(notesEl);
        } catch (err) {
          hide(loadingBox);
          errorBox.textContent = 'Sorry, could not compute player performance right now.';
          show(errorBox);
        } finally {
          btn.disabled = false;
        }
      }
  
      btn.addEventListener('click', fetchPlayerPerformance);
    })();
});