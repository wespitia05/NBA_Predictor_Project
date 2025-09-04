// wait until the html document is fully loaded before running this code
document.addEventListener('DOMContentLoaded', function () {
    (function () {      // immediately invoked function expression to keep variables scoped
        // get DOM elements from the top of the page
        const section = document.getElementById('predict-section'); // container with game info
        if (!section) return; // if not found, stop
      
        // game metadata (stored as data-* attributes on this section)
        const gameId = section.dataset.gameId;
        const homeName = section.dataset.homeName || 'Home Team';
        const awayName = section.dataset.awayName || 'Away Team';
      
        // ui elements (button, results, error, loading)
        const btn = document.getElementById('predict-btn');
        const resultsBox = document.getElementById('predict-results');
        const errorBox = document.getElementById('predict-error');
        const loadingBox = document.getElementById('predict-loading');
      
        // result fields
        const outcomeEl = document.getElementById('pred-outcome');      // prediction label
        const breakdownEl = document.getElementById('pred-breakdown');  // probabilities list
        const accuracyEl = document.getElementById('pred-accuracy');    // model accuracy
        const explainEl = document.getElementById('pred-explain');      // explanation details
      
        // small helper functions to hide/show elements
        function show(el) { el.classList.remove('hidden'); }
        function hide(el) { el.classList.add('hidden'); }

        // clear all outputs (used when starting new request)
        function resetOutputs() {
          hide(resultsBox);
          hide(errorBox);
          hide(loadingBox);
          outcomeEl.textContent = '';
          breakdownEl.innerHTML = '';
          accuracyEl.textContent = '';
          explainEl.innerHTML = '';
        }
      
        // async function: call the flask backend and display prediction results
        async function fetchPrediction() {
          // disable button + reset old outputs + show loading spinner
          btn.disabled = true;
          resetOutputs();
          show(loadingBox);
      
          try {
            // make GET request to flask api
            const res = await fetch(`/api/predict/${encodeURIComponent(gameId)}`);
            if (!res.ok) throw new Error('Request failed');
            const data = await res.json(); // parse response as json
      
            // display the outcome line (who is predicted to win)
            outcomeEl.textContent = data.prediction || `${homeName} vs ${awayName}`;
      
            // prob breakdown: away then home, to match your earlier layout
            const probs = data.probabilities || {};
            const awayPct = typeof probs.away === 'number' ? probs.away : null;
            const homePct = typeof probs.home === 'number' ? probs.home : null;
      
            // create <p> for away team %
            if (awayPct !== null) {
              const p = document.createElement('p');
              p.textContent = `${awayName}: ${awayPct.toFixed(2)}%`;
              breakdownEl.appendChild(p);
            }
            // create <p> for home team %
            if (homePct !== null) {
              const p = document.createElement('p');
              p.textContent = `${homeName}: ${homePct.toFixed(2)}%`;
              breakdownEl.appendChild(p);
            }
      
            // accuracy (training accuracy for now)
            if (typeof data.accuracy === 'number') {
              accuracyEl.textContent = `Model Accuracy: ${(data.accuracy * 100).toFixed(2)}%`;
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
      
              // build explanation html (h2h win %, rest days, weights)
              explainEl.innerHTML =
                `H2H (Home Last 6): <b>${h2hHomePct}%</b><br>` +
                `Rest Days — Home: <b>${homeRest}</b>, Away: <b>${awayRest}</b> ` +
                `(Diff <b>${restDiff}</b>, Bump <b>${restBumpPct}%</b>)<br>` +
                `Weights — Model: <b>${((w.model || 0) * 100).toFixed(0)}%</b>, ` +
                `H2H: <b>${((w.h2h || 0) * 100).toFixed(0)}%</b>, ` +
                `Home-Court: <b>${((w.home_court || 0) * 100).toFixed(0)}%</b>, ` +
                `Rest: <b>${((w.rest || 0) * 100).toFixed(0)}%</b>`;
            }
      
            // hide loading spinner + show results
            hide(loadingBox);
            show(resultsBox);
          } catch (err) {
            // on error, hide spinner, show error msg
            hide(loadingBox);
            errorBox.textContent = 'Sorry, could not compute probabilities right now.';
            show(errorBox);
          } finally {
            // always re-enable button
            btn.disabled = false;
          }
        }
        // attach click event listener to the button
        btn.addEventListener('click', fetchPrediction);
      })(); // end IIFE
});