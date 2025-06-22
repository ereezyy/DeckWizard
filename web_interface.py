#!/usr/bin/env python3
"""
DeckWizard Web Interface
A Flask-based web application for the DeckWizard card game management suite
"""

from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
import json
import os
from datetime import datetime
from deckwizard import CardDatabase, DeckManager, GameTracker, Card, Deck

app = Flask(__name__)
CORS(app)

# Initialize DeckWizard components
card_db = CardDatabase()
deck_manager = DeckManager()
game_tracker = GameTracker()

@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('index.html')

@app.route('/api/cards', methods=['GET'])
def get_cards():
    """Get all cards with optional filtering"""
    try:
        filters = {}
        if request.args.get('name'):
            filters['name'] = request.args.get('name')
        if request.args.get('type'):
            filters['card_type'] = request.args.get('type')
        if request.args.get('rarity'):
            filters['rarity'] = request.args.get('rarity')
        if request.args.get('cost'):
            filters['cost'] = int(request.args.get('cost'))
        
        cards = card_db.search_cards(**filters)
        return jsonify([{
            'id': card.id,
            'name': card.name,
            'cost': card.cost,
            'card_type': card.card_type,
            'rarity': card.rarity,
            'set_name': card.set_name,
            'description': card.description,
            'attack': card.attack,
            'health': card.health,
            'abilities': card.abilities
        } for card in cards])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/cards', methods=['POST'])
def add_card():
    """Add a new card"""
    try:
        data = request.json
        card = Card(
            id=data.get('id', f"card_{data['name'].lower().replace(' ', '_')}"),
            name=data['name'],
            cost=data['cost'],
            card_type=data['card_type'],
            rarity=data['rarity'],
            set_name=data['set_name'],
            description=data.get('description', ''),
            attack=data.get('attack'),
            health=data.get('health'),
            abilities=data.get('abilities', [])
        )
        
        success = card_db.add_card(card)
        if success:
            return jsonify({'message': 'Card added successfully', 'card_id': card.id})
        else:
            return jsonify({'error': 'Failed to add card'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/decks', methods=['GET'])
def get_decks():
    """Get all decks"""
    try:
        # This would need to be implemented in the DeckManager
        # For now, return empty list
        return jsonify([])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/decks', methods=['POST'])
def create_deck():
    """Create a new deck"""
    try:
        data = request.json
        deck = deck_manager.create_deck(data['name'], data['format'])
        return jsonify({
            'message': 'Deck created successfully',
            'deck_id': deck.id,
            'deck': {
                'id': deck.id,
                'name': deck.name,
                'format': deck.format,
                'cards': deck.cards,
                'created_date': deck.created_date,
                'last_modified': deck.last_modified
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/decks/<deck_id>/analyze', methods=['GET'])
def analyze_deck(deck_id):
    """Analyze a deck"""
    try:
        deck = deck_manager.load_deck(deck_id)
        if not deck:
            return jsonify({'error': 'Deck not found'}), 404
        
        analysis = deck_manager.analyze_deck(deck)
        return jsonify(analysis)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/decks/<deck_id>/cards', methods=['POST'])
def add_card_to_deck(deck_id):
    """Add cards to a deck"""
    try:
        data = request.json
        deck = deck_manager.load_deck(deck_id)
        if not deck:
            return jsonify({'error': 'Deck not found'}), 404
        
        success = deck_manager.add_card_to_deck(
            deck, 
            data['card_id'], 
            data.get('quantity', 1)
        )
        
        if success:
            return jsonify({'message': 'Card added to deck successfully'})
        else:
            return jsonify({'error': 'Failed to add card to deck'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/games', methods=['POST'])
def record_game():
    """Record a game result"""
    try:
        data = request.json
        success = game_tracker.record_game(
            data['deck_id'],
            data['opponent_deck'],
            data['result'],
            data['game_length'],
            data.get('notes', '')
        )
        
        if success:
            return jsonify({'message': 'Game recorded successfully'})
        else:
            return jsonify({'error': 'Failed to record game'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/decks/<deck_id>/stats', methods=['GET'])
def get_deck_stats(deck_id):
    """Get deck statistics"""
    try:
        stats = game_tracker.get_deck_statistics(deck_id)
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/import/cards', methods=['POST'])
def import_cards():
    """Import cards from various formats"""
    try:
        data = request.json
        format_type = data.get('format', 'json')
        cards_data = data.get('cards', [])
        
        imported_count = 0
        errors = []
        
        for card_data in cards_data:
            try:
                if format_type == 'mtg':
                    # Parse MTG format
                    card = parse_mtg_card(card_data)
                elif format_type == 'hearthstone':
                    # Parse Hearthstone format
                    card = parse_hearthstone_card(card_data)
                else:
                    # Default JSON format
                    card = Card(**card_data)
                
                if card_db.add_card(card):
                    imported_count += 1
                else:
                    errors.append(f"Failed to add card: {card.name}")
            except Exception as e:
                errors.append(f"Error parsing card: {str(e)}")
        
        return jsonify({
            'imported_count': imported_count,
            'errors': errors
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/export/deck/<deck_id>', methods=['GET'])
def export_deck(deck_id):
    """Export deck in various formats"""
    try:
        deck = deck_manager.load_deck(deck_id)
        if not deck:
            return jsonify({'error': 'Deck not found'}), 404
        
        format_type = request.args.get('format', 'json')
        
        if format_type == 'mtg':
            exported_data = export_deck_mtg(deck)
        elif format_type == 'arena':
            exported_data = export_deck_arena(deck)
        else:
            exported_data = {
                'name': deck.name,
                'format': deck.format,
                'cards': deck.cards,
                'created_date': deck.created_date,
                'last_modified': deck.last_modified
            }
        
        return jsonify(exported_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/optimize/deck/<deck_id>', methods=['POST'])
def optimize_deck(deck_id):
    """Optimize deck composition"""
    try:
        deck = deck_manager.load_deck(deck_id)
        if not deck:
            return jsonify({'error': 'Deck not found'}), 404
        
        optimization_type = request.json.get('type', 'mana_curve')
        
        if optimization_type == 'mana_curve':
            suggestions = optimize_mana_curve(deck)
        elif optimization_type == 'card_synergy':
            suggestions = optimize_card_synergy(deck)
        else:
            suggestions = []
        
        return jsonify({
            'suggestions': suggestions,
            'current_analysis': deck_manager.analyze_deck(deck)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/tournament/bracket', methods=['POST'])
def generate_tournament_bracket():
    """Generate tournament bracket"""
    try:
        data = request.json
        participants = data.get('participants', [])
        tournament_type = data.get('type', 'single_elimination')
        
        if tournament_type == 'single_elimination':
            bracket = generate_single_elimination_bracket(participants)
        elif tournament_type == 'double_elimination':
            bracket = generate_double_elimination_bracket(participants)
        else:
            bracket = generate_round_robin_bracket(participants)
        
        return jsonify(bracket)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Helper functions for card parsing and export
def parse_mtg_card(card_data):
    """Parse MTG format card data"""
    return Card(
        id=card_data.get('id', card_data['name'].lower().replace(' ', '_')),
        name=card_data['name'],
        cost=card_data.get('cmc', 0),
        card_type=card_data.get('type_line', 'Unknown'),
        rarity=card_data.get('rarity', 'common').title(),
        set_name=card_data.get('set_name', 'Unknown'),
        description=card_data.get('oracle_text', ''),
        attack=card_data.get('power'),
        health=card_data.get('toughness'),
        abilities=card_data.get('keywords', [])
    )

def parse_hearthstone_card(card_data):
    """Parse Hearthstone format card data"""
    return Card(
        id=card_data.get('cardId', card_data['name'].lower().replace(' ', '_')),
        name=card_data['name'],
        cost=card_data.get('cost', 0),
        card_type=card_data.get('type', 'Unknown'),
        rarity=card_data.get('rarity', 'COMMON').title(),
        set_name=card_data.get('cardSet', 'Unknown'),
        description=card_data.get('text', ''),
        attack=card_data.get('attack'),
        health=card_data.get('health'),
        abilities=card_data.get('mechanics', [])
    )

def export_deck_mtg(deck):
    """Export deck in MTG format"""
    cards_list = []
    for card_id, quantity in deck.cards.items():
        card = card_db.get_card(card_id)
        if card:
            cards_list.append(f"{quantity} {card.name}")
    
    return {
        'name': deck.name,
        'format': deck.format,
        'mainboard': cards_list,
        'sideboard': []
    }

def export_deck_arena(deck):
    """Export deck in MTG Arena format"""
    cards_list = []
    for card_id, quantity in deck.cards.items():
        card = card_db.get_card(card_id)
        if card:
            cards_list.append(f"{quantity} {card.name} ({card.set_name}) {card.id}")
    
    return {
        'deck': '\n'.join(cards_list)
    }

def optimize_mana_curve(deck):
    """Optimize deck mana curve"""
    analysis = deck_manager.analyze_deck(deck)
    suggestions = []
    
    curve = analysis.get('mana_curve', {})
    total_cards = analysis.get('total_cards', 0)
    
    # Check for too many high-cost cards
    high_cost_cards = sum(curve.get(str(i), 0) for i in range(6, 11))
    if high_cost_cards > total_cards * 0.2:
        suggestions.append({
            'type': 'reduce_high_cost',
            'message': 'Consider reducing high-cost cards (6+ mana) for better early game',
            'priority': 'high'
        })
    
    # Check for lack of early game
    early_game = sum(curve.get(str(i), 0) for i in range(1, 4))
    if early_game < total_cards * 0.3:
        suggestions.append({
            'type': 'add_early_game',
            'message': 'Add more low-cost cards (1-3 mana) for better early game presence',
            'priority': 'high'
        })
    
    return suggestions

def optimize_card_synergy(deck):
    """Optimize card synergies"""
    suggestions = []
    
    # This would analyze card types and suggest synergies
    suggestions.append({
        'type': 'synergy',
        'message': 'Consider adding more cards that synergize with your existing strategy',
        'priority': 'medium'
    })
    
    return suggestions

def generate_single_elimination_bracket(participants):
    """Generate single elimination tournament bracket"""
    import math
    
    # Pad to next power of 2
    bracket_size = 2 ** math.ceil(math.log2(len(participants)))
    padded_participants = participants + [None] * (bracket_size - len(participants))
    
    rounds = []
    current_round = padded_participants
    
    while len(current_round) > 1:
        next_round = []
        matches = []
        
        for i in range(0, len(current_round), 2):
            player1 = current_round[i]
            player2 = current_round[i + 1] if i + 1 < len(current_round) else None
            
            matches.append({
                'player1': player1,
                'player2': player2,
                'winner': None
            })
            
            # Auto-advance if one player is None (bye)
            if player2 is None:
                next_round.append(player1)
            else:
                next_round.append(None)  # TBD
        
        rounds.append(matches)
        current_round = next_round
    
    return {
        'type': 'single_elimination',
        'rounds': rounds,
        'participants': participants
    }

def generate_double_elimination_bracket(participants):
    """Generate double elimination tournament bracket"""
    # Simplified double elimination
    winners_bracket = generate_single_elimination_bracket(participants)
    
    return {
        'type': 'double_elimination',
        'winners_bracket': winners_bracket,
        'losers_bracket': {'rounds': []},
        'participants': participants
    }

def generate_round_robin_bracket(participants):
    """Generate round robin tournament bracket"""
    matches = []
    
    for i, player1 in enumerate(participants):
        for j, player2 in enumerate(participants[i+1:], i+1):
            matches.append({
                'player1': player1,
                'player2': player2,
                'result': None
            })
    
    return {
        'type': 'round_robin',
        'matches': matches,
        'participants': participants
    }

if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static', exist_ok=True)
    
    print("🃏 DeckWizard Web Interface Starting...")
    print("📊 Features: Card Management, Deck Building, Analytics, Tournament Brackets")
    print("🌐 Access at: http://localhost:5000")
    
    app.run(host='0.0.0.0', port=5000, debug=True)

