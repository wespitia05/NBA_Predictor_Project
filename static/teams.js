// wait until the page's html content is fully loaded before running this code
document.addEventListener('DOMContentLoaded', () => {
    // select the first button in the button container (eastern)
    const eastBtn = document.querySelector('.button-container a:first-child');
    // select the second button in the button container (western)
    const westBtn = document.querySelector('.button-container a:last-child');

    // get grid container for eastern with its id
    const eastTeams = document.getElementById('eastern-teams');
    // get grid container for western with its id
    const westTeams = document.getElementById('western-teams');

    // helper to highlight active button
    function setActive(buttonClicked, buttonOther) {
        // active button gets highlighted
        buttonClicked.classList.add('active');
        // other button gets unhighlighted
        buttonOther.classList.remove('active');
    }

    // eastern button when clicked
    eastBtn.addEventListener('click', (event) => {
        event.preventDefault(); // no page jump
        // display eastern teams
        eastTeams.style.display = 'grid';
        // hide western teams
        westTeams.style.display = 'none';
        // highlight eastern button, unhighlight western button
        setActive(eastBtn, westBtn);
    });

    // western button when clicked
    westBtn.addEventListener('click', (event) => {
        event.preventDefault(); // no page jump
        // display western teams
        westTeams.style.display = 'grid';
        // hide eastern teams
        eastTeams.style.display = 'none';
        // highlight western button, unhighlight eastern button
        setActive(westBtn, eastBtn);
    });
});