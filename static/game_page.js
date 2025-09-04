// wait until the html document is fully loaded before running this code
document.addEventListener('DOMContentLoaded', function () {
    (function () {      // immediately invoked function expression to keep variables scoped
      // get DOM elements from the top of the page
      const section = document.getElementById('predict-section'); // container with game info
      if (!section) return; // if not found, stop
  
      // game metadata (stored as data-* attributes on this section)
      const gameId   = section.dataset.gameId;
      const homeName = section.dataset.homeName || 'Home Team';
      const awayName = section.dataset.awayName || 'Away Team';
  
      // ui elements (button, results, error, loading)
      const btn        = document.getElementById('predict-btn');
      const resultsBox = document.getElementById('predict-results');
      const errorBox   = document.getElementById('predict-error');
      const loadingBox = document.getElementById('predict-loading');
  
      // result fields
      const accuracyEl  = document.getElementById('pred-accuracy');     // model accuracy
      const explainEl   = document.getElementById('pred-explain');      // explanation details
      const tableBody   = document.getElementById('pred-table-body');   // tbody where rows go
  
      // small helper functions to hide/show elements
      function show(el) { el.classList.remove('hidden'); }
      function hide(el) { el.classList.add('hidden'); }
  
      // clear all outputs (used when starting new request)
      function resetOutputs() {
        hide(resultsBox);
        hide(errorBox);
        hide(loadingBox);
        accuracyEl.textContent = '';
        explainEl.innerHTML = '';
        if (tableBody) tableBody.innerHTML = '';
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
  
          // probabilities (away then home)
          const probs   = data.probabilities || {};
          const awayPct = typeof probs.away === 'number' ? probs.away : null;
          const homePct = typeof probs.home === 'number' ? probs.home : null;
  
          // build the 2-row table and highlight the winner row
          if (tableBody) {
            tableBody.innerHTML = '';
  
            if (awayPct !== null && homePct !== null) {
              const homeWins = homePct >= awayPct;
  
              // away row
              const trAway = document.createElement('tr');
              if (!homeWins) trAway.classList.add('winner');
              trAway.innerHTML = `
                <td>${awayName}</td>
                <td>${awayPct.toFixed(2)}%</td>
              `;
              tableBody.appendChild(trAway);
  
              // home row
              const trHome = document.createElement('tr');
              if (homeWins) trHome.classList.add('winner');
              trHome.innerHTML = `
                <td>${homeName}</td>
                <td>${homePct.toFixed(2)}%</td>
              `;
              tableBody.appendChild(trHome);
            } else {
              // fallback: if only one number available, show whichever we have
              if (awayPct !== null) {
                const tr = document.createElement('tr');
                tr.innerHTML = `<td>${awayName}</td><td>${awayPct.toFixed(2)}%</td>`;
                tableBody.appendChild(tr);
              }
              if (homePct !== null) {
                const tr = document.createElement('tr');
                tr.innerHTML = `<td>${homeName}</td><td>${homePct.toFixed(2)}%</td>`;
                tableBody.appendChild(tr);
              }
            }
          }
  
          // accuracy (training accuracy for now)
          if (typeof data.accuracy === 'number') {
            accuracyEl.textContent = `Model Accuracy: ${(data.accuracy * 100).toFixed(2)}%`;
          }
  
          // explain (H2H, rest, weights)
          if (data.explain) {
            const e = data.explain;
            const h2hHomePct  = typeof e.h2h_home === 'number' ? (e.h2h_home * 100).toFixed(1) : '—';
            const homeRest    = (e.home_rest_days ?? '—');
            const awayRest    = (e.away_rest_days ?? '—');
            const restDiff    = (e.rest_diff ?? '—');
            const restBumpPct = typeof e.rest_bump === 'number' ? (e.rest_bump * 100).toFixed(1) : '—';
            const w = e.weights || {};
  
            // build explanation html (h2h win %, rest days, weights)
            explainEl.innerHTML = `
                <details>
                    <summary><b>Head-to-Head (H2H): </b>${h2hHomePct}%</summary>
                    <div>
                    Meaning: In the most recent head-to-head games (up to 6), this is the share the
                    <b>home team</b> won. 50% ≈ even; higher favors the home team.
                    </div>
                </details>

                <details>
                    <summary><b>Rest Days: </b>Home Team Rested <b>${homeRest}</b> days, Away Team Rested <b>${awayRest}</b> days</summary>
                    <div>
                    Difference (Home − Away): <b>${restDiff}</b><br>
                    Rest Bump applied: <b>${restBumpPct}%</b><br>
                    Meaning: More days since the previous game = more rest. Positive
                    difference means the home team is more rested. Each day of rest is
                    worth about <b>+2%</b> in win probability, capped at ±3 days (±6%).
                    </div>
                </details>

                <details>
                    <summary><b>Weights</b>
                        Model <b>${((w.model || 0) * 100).toFixed(0)}%</b>,
                        H2H <b>${((w.h2h || 0) * 100).toFixed(0)}%</b>,
                        Home-Court <b>${((w.home_court || 0) * 100).toFixed(0)}%</b>,
                        Rest <b>${((w.rest || 0) * 100).toFixed(0)}%</b>
                    </summary>
                    <div>
                    Meaning: Each percentage shows how much that factor contributes
                    to the blended score before normalization. The “Model” is the main
                    logistic regression signal; the others are smaller nudges.
                    </div>
                </details>
                `;
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