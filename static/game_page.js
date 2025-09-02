document.addEventListener('DOMContentLoaded', function () {
    (function () {
        // get DOM elements
        const section = document.getElementById('predict-section');
        if (!section) return;
      
        const gameId = section.dataset.gameId;
        const homeName = section.dataset.homeName || 'Home Team';
        const awayName = section.dataset.awayName || 'Away Team';
      
        const btn = document.getElementById('predict-btn');
        const resultsBox = document.getElementById('predict-results');
        const errorBox = document.getElementById('predict-error');
        const loadingBox = document.getElementById('predict-loading');
      
        const outcomeEl = document.getElementById('pred-outcome');
        const breakdownEl = document.getElementById('pred-breakdown');
        const accuracyEl = document.getElementById('pred-accuracy');
        const explainEl = document.getElementById('pred-explain');
      
        function show(el) { el.classList.remove('hidden'); }
        function hide(el) { el.classList.add('hidden'); }
        function resetOutputs() {
          hide(resultsBox);
          hide(errorBox);
          hide(loadingBox);
          outcomeEl.textContent = '';
          breakdownEl.innerHTML = '';
          accuracyEl.textContent = '';
          explainEl.innerHTML = '';
        }
      
        async function fetchPrediction() {
          // prepare UI
          btn.disabled = true;
          resetOutputs();
          show(loadingBox);
      
          try {
            const res = await fetch(`/api/predict/${encodeURIComponent(gameId)}`);
            if (!res.ok) throw new Error('Request failed');
            const data = await res.json();
      
            // outcome line
            outcomeEl.textContent = data.prediction || `${homeName} vs ${awayName}`;
      
            // prob breakdown: away then home, to match your earlier layout
            const probs = data.probabilities || {};
            const awayPct = typeof probs.away === 'number' ? probs.away : null;
            const homePct = typeof probs.home === 'number' ? probs.home : null;
      
            if (awayPct !== null) {
              const li = document.createElement('li');
              li.textContent = `${awayName}: ${awayPct.toFixed(2)}%`;
              breakdownEl.appendChild(li);
            }
            if (homePct !== null) {
              const li = document.createElement('li');
              li.textContent = `${homeName}: ${homePct.toFixed(2)}%`;
              breakdownEl.appendChild(li);
            }
      
            // accuracy (training accuracy for now)
            if (typeof data.accuracy === 'number') {
              accuracyEl.textContent = `Model accuracy (train): ${(data.accuracy * 100).toFixed(2)}%`;
            }
      
            // explain (H2H, rest, weights)
            if (data.explain) {
              const e = data.explain;
              const h2hHomePct = typeof e.h2h_home === 'number' ? (e.h2h_home * 100).toFixed(1) : '—';
              const homeRest = (e.home_rest_days ?? '—');
              const awayRest = (e.away_rest_days ?? '—');
              const restDiff = (e.rest_diff ?? '—');
              const restBumpPct = typeof e.rest_bump === 'number' ? (e.rest_bump * 100).toFixed(1) : '—';
              const w = e.weights || {};
      
              explainEl.innerHTML =
                `H2H (home last 6): <b>${h2hHomePct}%</b><br>` +
                `Rest days — home: <b>${homeRest}</b>, away: <b>${awayRest}</b> ` +
                `(diff <b>${restDiff}</b>, bump <b>${restBumpPct}%</b>)<br>` +
                `Weights — model: <b>${((w.model || 0) * 100).toFixed(0)}%</b>, ` +
                `H2H: <b>${((w.h2h || 0) * 100).toFixed(0)}%</b>, ` +
                `home-court: <b>${((w.home_court || 0) * 100).toFixed(0)}%</b>, ` +
                `rest: <b>${((w.rest || 0) * 100).toFixed(0)}%</b>`;
            }
      
            hide(loadingBox);
            show(resultsBox);
          } catch (err) {
            hide(loadingBox);
            errorBox.textContent = 'Sorry, could not compute probabilities right now.';
            show(errorBox);
          } finally {
            btn.disabled = false;
          }
        }
      
        btn.addEventListener('click', fetchPrediction);
      })();
});