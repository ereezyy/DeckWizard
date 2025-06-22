// DeckWizard Web Interface JavaScript
class DeckWizardApp {
    constructor() {
        this.apiBase = '/api';
        this.cards = [];
        this.decks = [];
        this.currentDeck = null;
        
        this.init();
    }

    async init() {
        this.setupEventListeners();
        await this.loadDashboardData();
        await this.loadCards();
        await this.loadDecks();
        this.setupCharts();
    }

    setupEventListeners() {
        // Navigation
        document.querySelectorAll('.nav-link').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const target = e.target.getAttribute('href').substring(1);
                this.scrollToSection(target);
            });
        });

        // Add Card Modal
        document.getElementById('add-card-btn').addEventListener('click', () => {
            this.showModal('add-card-modal');
        });
        
        document.getElementById('close-add-card-modal').addEventListener('click', () => {
            this.hideModal('add-card-modal');
        });
        
        document.getElementById('cancel-add-card').addEventListener('click', () => {
            this.hideModal('add-card-modal');
        });

        // Create Deck Modal
        document.getElementById('create-deck-btn').addEventListener('click', () => {
            this.showModal('create-deck-modal');
        });
        
        document.getElementById('close-create-deck-modal').addEventListener('click', () => {
            this.hideModal('create-deck-modal');
        });
        
        document.getElementById('cancel-create-deck').addEventListener('click', () => {
            this.hideModal('create-deck-modal');
        });

        // Forms
        document.getElementById('add-card-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.addCard();
        });
        
        document.getElementById('create-deck-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.createDeck();
        });

        // Filters
        document.getElementById('filter-cards-btn').addEventListener('click', () => {
            this.filterCards();
        });

        // Tournament
        document.getElementById('generate-bracket-btn').addEventListener('click', () => {
            this.generateTournamentBracket();
        });
    }

    scrollToSection(sectionId) {
        const section = document.getElementById(sectionId);
        if (section) {
            section.scrollIntoView({ behavior: 'smooth' });
        }
    }

    showModal(modalId) {
        const modal = document.getElementById(modalId);
        modal.classList.remove('hidden');
        modal.classList.add('flex');
    }

    hideModal(modalId) {
        const modal = document.getElementById(modalId);
        modal.classList.add('hidden');
        modal.classList.remove('flex');
    }

    async loadDashboardData() {
        try {
            // Load basic statistics
            const cards = await this.apiCall('/cards');
            const decks = await this.apiCall('/decks');
            
            document.getElementById('total-cards').textContent = cards.length;
            document.getElementById('total-decks').textContent = decks.length;
            
            // These would come from actual game data
            document.getElementById('total-games').textContent = '42';
            document.getElementById('win-rate').textContent = '68%';
        } catch (error) {
            console.error('Error loading dashboard data:', error);
        }
    }

    async loadCards() {
        try {
            this.cards = await this.apiCall('/cards');
            this.renderCards(this.cards);
        } catch (error) {
            console.error('Error loading cards:', error);
            this.showNotification('Error loading cards', 'error');
        }
    }

    async loadDecks() {
        try {
            this.decks = await this.apiCall('/decks');
            this.renderDecks(this.decks);
        } catch (error) {
            console.error('Error loading decks:', error);
        }
    }

    renderCards(cards) {
        const grid = document.getElementById('cards-grid');
        grid.innerHTML = '';

        if (cards.length === 0) {
            grid.innerHTML = `
                <div class="col-span-full text-center py-12">
                    <i class="fas fa-cards-blank text-gray-400 text-6xl mb-4"></i>
                    <p class="text-gray-600 text-lg">No cards found. Add some cards to get started!</p>
                </div>
            `;
            return;
        }

        cards.forEach(card => {
            const cardElement = this.createCardElement(card);
            grid.appendChild(cardElement);
        });
    }

    createCardElement(card) {
        const div = document.createElement('div');
        div.className = 'bg-white rounded-lg shadow-md p-4 hover:shadow-lg transition-shadow';
        
        const rarityColors = {
            'Common': 'bg-gray-500',
            'Uncommon': 'bg-green-500',
            'Rare': 'bg-blue-500',
            'Epic': 'bg-purple-500',
            'Legendary': 'bg-yellow-500'
        };

        div.innerHTML = `
            <div class="flex items-start justify-between mb-3">
                <div class="flex-1">
                    <h3 class="font-bold text-lg text-gray-800">${card.name}</h3>
                    <p class="text-sm text-gray-600">${card.card_type}</p>
                </div>
                <div class="flex items-center space-x-2">
                    <span class="bg-blue-100 text-blue-800 px-2 py-1 rounded-full text-sm font-semibold">
                        ${card.cost}
                    </span>
                    <span class="${rarityColors[card.rarity] || 'bg-gray-500'} text-white px-2 py-1 rounded-full text-xs font-semibold">
                        ${card.rarity}
                    </span>
                </div>
            </div>
            
            ${card.description ? `<p class="text-sm text-gray-700 mb-3">${card.description}</p>` : ''}
            
            ${card.attack !== null || card.health !== null ? `
                <div class="flex items-center justify-between text-sm">
                    <span class="text-gray-600">${card.set_name}</span>
                    <div class="flex space-x-2">
                        ${card.attack !== null ? `<span class="text-red-600 font-semibold">${card.attack} ATK</span>` : ''}
                        ${card.health !== null ? `<span class="text-green-600 font-semibold">${card.health} HP</span>` : ''}
                    </div>
                </div>
            ` : `<p class="text-sm text-gray-600">${card.set_name}</p>`}
            
            <div class="mt-3 flex space-x-2">
                <button onclick="deckWizard.addCardToDeck('${card.id}')" 
                        class="flex-1 bg-blue-500 hover:bg-blue-600 text-white px-3 py-1 rounded text-sm transition-colors">
                    Add to Deck
                </button>
                <button onclick="deckWizard.editCard('${card.id}')" 
                        class="bg-gray-500 hover:bg-gray-600 text-white px-3 py-1 rounded text-sm transition-colors">
                    Edit
                </button>
            </div>
        `;

        return div;
    }

    renderDecks(decks) {
        const grid = document.getElementById('decks-grid');
        grid.innerHTML = '';

        if (decks.length === 0) {
            grid.innerHTML = `
                <div class="col-span-full text-center py-12">
                    <i class="fas fa-layer-group text-gray-400 text-6xl mb-4"></i>
                    <p class="text-gray-600 text-lg">No decks created yet. Create your first deck!</p>
                </div>
            `;
            return;
        }

        decks.forEach(deck => {
            const deckElement = this.createDeckElement(deck);
            grid.appendChild(deckElement);
        });
    }

    createDeckElement(deck) {
        const div = document.createElement('div');
        div.className = 'bg-white rounded-lg shadow-md p-6 hover:shadow-lg transition-shadow';
        
        const cardCount = Object.values(deck.cards || {}).reduce((sum, count) => sum + count, 0);

        div.innerHTML = `
            <div class="flex items-start justify-between mb-4">
                <div>
                    <h3 class="font-bold text-xl text-gray-800">${deck.name}</h3>
                    <p class="text-sm text-gray-600">${deck.format}</p>
                </div>
                <span class="bg-green-100 text-green-800 px-3 py-1 rounded-full text-sm font-semibold">
                    ${cardCount} cards
                </span>
            </div>
            
            <div class="text-sm text-gray-600 mb-4">
                <p>Created: ${new Date(deck.created_date).toLocaleDateString()}</p>
                <p>Modified: ${new Date(deck.last_modified).toLocaleDateString()}</p>
            </div>
            
            <div class="flex space-x-2">
                <button onclick="deckWizard.viewDeck('${deck.id}')" 
                        class="flex-1 bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded transition-colors">
                    View Deck
                </button>
                <button onclick="deckWizard.analyzeDeck('${deck.id}')" 
                        class="bg-purple-500 hover:bg-purple-600 text-white px-4 py-2 rounded transition-colors">
                    Analyze
                </button>
            </div>
        `;

        return div;
    }

    async addCard() {
        try {
            const formData = {
                name: document.getElementById('card-name').value,
                cost: parseInt(document.getElementById('card-cost').value),
                card_type: document.getElementById('card-type').value,
                rarity: document.getElementById('card-rarity').value,
                set_name: document.getElementById('card-set').value,
                description: document.getElementById('card-description').value,
                attack: document.getElementById('card-attack').value ? parseInt(document.getElementById('card-attack').value) : null,
                health: document.getElementById('card-health').value ? parseInt(document.getElementById('card-health').value) : null
            };

            await this.apiCall('/cards', 'POST', formData);
            this.hideModal('add-card-modal');
            this.showNotification('Card added successfully!', 'success');
            await this.loadCards();
            await this.loadDashboardData();
            
            // Reset form
            document.getElementById('add-card-form').reset();
        } catch (error) {
            console.error('Error adding card:', error);
            this.showNotification('Error adding card', 'error');
        }
    }

    async createDeck() {
        try {
            const formData = {
                name: document.getElementById('deck-name').value,
                format: document.getElementById('deck-format').value
            };

            await this.apiCall('/decks', 'POST', formData);
            this.hideModal('create-deck-modal');
            this.showNotification('Deck created successfully!', 'success');
            await this.loadDecks();
            await this.loadDashboardData();
            
            // Reset form
            document.getElementById('create-deck-form').reset();
        } catch (error) {
            console.error('Error creating deck:', error);
            this.showNotification('Error creating deck', 'error');
        }
    }

    async filterCards() {
        const filters = {
            name: document.getElementById('card-name-filter').value,
            type: document.getElementById('card-type-filter').value,
            rarity: document.getElementById('card-rarity-filter').value
        };

        try {
            const filteredCards = await this.apiCall('/cards', 'GET', null, filters);
            this.renderCards(filteredCards);
        } catch (error) {
            console.error('Error filtering cards:', error);
            this.showNotification('Error filtering cards', 'error');
        }
    }

    async generateTournamentBracket() {
        const type = document.getElementById('tournament-type').value;
        const participantsText = document.getElementById('tournament-participants').value;
        const participants = participantsText.split('\n').filter(p => p.trim());

        if (participants.length < 2) {
            this.showNotification('Please enter at least 2 participants', 'error');
            return;
        }

        try {
            const bracket = await this.apiCall('/tournament/bracket', 'POST', {
                type: type,
                participants: participants
            });

            this.renderTournamentBracket(bracket);
            this.showNotification('Tournament bracket generated!', 'success');
        } catch (error) {
            console.error('Error generating bracket:', error);
            this.showNotification('Error generating tournament bracket', 'error');
        }
    }

    renderTournamentBracket(bracket) {
        const container = document.getElementById('tournament-bracket');
        container.innerHTML = '';

        if (bracket.type === 'single_elimination') {
            this.renderSingleEliminationBracket(bracket, container);
        } else if (bracket.type === 'round_robin') {
            this.renderRoundRobinBracket(bracket, container);
        }
    }

    renderSingleEliminationBracket(bracket, container) {
        const div = document.createElement('div');
        div.className = 'space-y-6';

        bracket.rounds.forEach((round, roundIndex) => {
            const roundDiv = document.createElement('div');
            roundDiv.className = 'bg-gray-50 rounded-lg p-4';
            roundDiv.innerHTML = `
                <h4 class="font-semibold text-lg mb-4">Round ${roundIndex + 1}</h4>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                    ${round.map((match, matchIndex) => `
                        <div class="bg-white rounded border p-3">
                            <div class="flex justify-between items-center">
                                <span class="font-medium">${match.player1 || 'BYE'}</span>
                                <span class="text-gray-400">vs</span>
                                <span class="font-medium">${match.player2 || 'BYE'}</span>
                            </div>
                            ${match.winner ? `<div class="text-center mt-2 text-green-600 font-semibold">Winner: ${match.winner}</div>` : ''}
                        </div>
                    `).join('')}
                </div>
            `;
            div.appendChild(roundDiv);
        });

        container.appendChild(div);
    }

    renderRoundRobinBracket(bracket, container) {
        const div = document.createElement('div');
        div.className = 'bg-gray-50 rounded-lg p-4';
        
        div.innerHTML = `
            <h4 class="font-semibold text-lg mb-4">Round Robin Matches</h4>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                ${bracket.matches.map(match => `
                    <div class="bg-white rounded border p-3">
                        <div class="flex justify-between items-center">
                            <span class="font-medium">${match.player1}</span>
                            <span class="text-gray-400">vs</span>
                            <span class="font-medium">${match.player2}</span>
                        </div>
                    </div>
                `).join('')}
            </div>
        `;

        container.appendChild(div);
    }

    setupCharts() {
        // Performance Chart
        const performanceCtx = document.getElementById('performance-chart').getContext('2d');
        new Chart(performanceCtx, {
            type: 'line',
            data: {
                labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
                datasets: [{
                    label: 'Win Rate',
                    data: [65, 68, 70, 72, 69, 75],
                    borderColor: 'rgb(59, 130, 246)',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    tension: 0.4
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

        // Distribution Chart
        const distributionCtx = document.getElementById('distribution-chart').getContext('2d');
        new Chart(distributionCtx, {
            type: 'doughnut',
            data: {
                labels: ['Creatures', 'Spells', 'Artifacts', 'Enchantments'],
                datasets: [{
                    data: [45, 30, 15, 10],
                    backgroundColor: [
                        'rgb(34, 197, 94)',
                        'rgb(59, 130, 246)',
                        'rgb(168, 85, 247)',
                        'rgb(245, 158, 11)'
                    ]
                }]
            },
            options: {
                responsive: true
            }
        });
    }

    async apiCall(endpoint, method = 'GET', data = null, params = null) {
        let url = this.apiBase + endpoint;
        
        if (params) {
            const searchParams = new URLSearchParams(params);
            url += '?' + searchParams.toString();
        }

        const options = {
            method: method,
            headers: {
                'Content-Type': 'application/json'
            }
        };

        if (data) {
            options.body = JSON.stringify(data);
        }

        const response = await fetch(url, options);
        
        if (!response.ok) {
            throw new Error(`API call failed: ${response.statusText}`);
        }

        return await response.json();
    }

    showNotification(message, type = 'info') {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `fixed top-4 right-4 p-4 rounded-lg shadow-lg z-50 ${
            type === 'success' ? 'bg-green-500 text-white' :
            type === 'error' ? 'bg-red-500 text-white' :
            'bg-blue-500 text-white'
        }`;
        notification.textContent = message;

        document.body.appendChild(notification);

        // Remove after 3 seconds
        setTimeout(() => {
            notification.remove();
        }, 3000);
    }

    // Placeholder methods for future implementation
    async addCardToDeck(cardId) {
        this.showNotification('Add to deck functionality coming soon!', 'info');
    }

    async editCard(cardId) {
        this.showNotification('Edit card functionality coming soon!', 'info');
    }

    async viewDeck(deckId) {
        this.showNotification('View deck functionality coming soon!', 'info');
    }

    async analyzeDeck(deckId) {
        try {
            const analysis = await this.apiCall(`/decks/${deckId}/analyze`);
            this.showNotification(`Deck analysis: ${analysis.total_cards} cards, ${analysis.recommendations.length} recommendations`, 'success');
        } catch (error) {
            this.showNotification('Error analyzing deck', 'error');
        }
    }
}

// Initialize the application when the page loads
let deckWizard;
document.addEventListener('DOMContentLoaded', () => {
    deckWizard = new DeckWizardApp();
});

