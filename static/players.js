// keep track of how many players we've already loaded
let offset = 5;

document.addEventListener("DOMContentLoaded", function () {
    // get the button and table body from the html
    const loadButton = document.querySelector(".load-players-button");
    const tableBody = document.querySelector("table tbody");

    // read current search query (empty string if none)
    const currentQuery = loadButton?.dataset?.query || "";

    // when the load more players button is clicked
    loadButton.addEventListener("click", function (e) {
        // stops from reloading page
        e.preventDefault();
        // shows loading text
        loadButton.textContent = "Loading...";

        // ask server for next 5 players
        fetch(`/load_players?offset=${offset}&q=${encodeURIComponent(currentQuery)}`).then(response => response.json()).then(data => {
            // for each player we get back
            data.forEach(player => {
                // create new row in the table
                const row = document.createElement("tr");
                row.innerHTML = `
                    <td>${player.id}</td>
                    <td>
                        <a href="/player_stats/${player.id}" class="player-link">
                            ${player.full_name}
                        </a>
                    </td>
                    <td>${player.team_name}</td>
                    <td>${player.position}</td>
                `;
                // add row to the table
                tableBody.appendChild(row)
            });

            // update how many players we've loaded
            offset += data.length;

            // change button text back to normal
            loadButton.textContent = "Load More Players"
        }).catch(error => {
            // if something goes wrong, show error in console
            console.error("error loading players: ", error);
            loadButton.textContent = "Load More Players"
        })
    })
})