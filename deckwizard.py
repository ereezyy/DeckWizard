#!/usr/bin/env python3
"""
DeckWizard - Advanced Card Game Management Suite
A comprehensive tool for managing card collections, deck building, and game analysis
Author: ereezyy
Version: 1.0.0
"""

import json
import sqlite3
import random
import argparse
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('deckwizard.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class Card:
    """Represents a single card in the collection"""
    id: str
    name: str
    cost: int
    card_type: str
    rarity: str
    set_name: str
    description: str
    attack: Optional[int] = None
    health: Optional[int] = None
    abilities: List[str] = None
    
    def __post_init__(self):
        if self.abilities is None:
            self.abilities = []

@dataclass
class Deck:
    """Represents a deck configuration"""
    id: str
    name: str
    format: str
    cards: Dict[str, int]  # card_id -> quantity
    created_date: str
    last_modified: str
    win_rate: float = 0.0
    games_played: int = 0
    
    def get_total_cards(self) -> int:
        return sum(self.cards.values())
    
    def get_mana_curve(self) -> Dict[int, int]:
        """Calculate mana curve distribution"""
        curve = {}
        for card_id, quantity in self.cards.items():
            # This would need card database lookup in real implementation
            cost = 3  # Placeholder
            curve[cost] = curve.get(cost, 0) + quantity
        return curve

@dataclass
class GameResult:
    """Represents a game result"""
    id: str
    deck_id: str
    opponent_deck: str
    result: str  # 'win', 'loss', 'draw'
    game_length: int  # in turns
    date_played: str
    notes: str = ""

class CardDatabase:
    """Manages the card database and collection"""
    
    def __init__(self, db_path: str = "deckwizard.db"):
        self.db_path = db_path
        self.init_database()
        
    def init_database(self):
        """Initialize the SQLite database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Cards table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cards (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                cost INTEGER NOT NULL,
                card_type TEXT NOT NULL,
                rarity TEXT NOT NULL,
                set_name TEXT NOT NULL,
                description TEXT,
                attack INTEGER,
                health INTEGER,
                abilities TEXT
            )
        ''')
        
        # Collection table (owned cards)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS collection (
                card_id TEXT,
                quantity INTEGER DEFAULT 1,
                condition TEXT DEFAULT 'mint',
                acquired_date TEXT,
                FOREIGN KEY (card_id) REFERENCES cards (id)
            )
        ''')
        
        # Decks table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS decks (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                format TEXT NOT NULL,
                cards TEXT,  -- JSON string
                created_date TEXT,
                last_modified TEXT,
                win_rate REAL DEFAULT 0.0,
                games_played INTEGER DEFAULT 0
            )
        ''')
        
        # Game results table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS game_results (
                id TEXT PRIMARY KEY,
                deck_id TEXT,
                opponent_deck TEXT,
                result TEXT,
                game_length INTEGER,
                date_played TEXT,
                notes TEXT,
                FOREIGN KEY (deck_id) REFERENCES decks (id)
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Database initialized successfully")
    
    def add_card(self, card: Card) -> bool:
        """Add a card to the database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO cards 
                (id, name, cost, card_type, rarity, set_name, description, attack, health, abilities)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                card.id, card.name, card.cost, card.card_type, card.rarity,
                card.set_name, card.description, card.attack, card.health,
                json.dumps(card.abilities)
            ))
            
            conn.commit()
            conn.close()
            logger.info(f"Added card: {card.name}")
            return True
        except Exception as e:
            logger.error(f"Error adding card: {e}")
            return False
    
    def get_card(self, card_id: str) -> Optional[Card]:
        """Retrieve a card by ID"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM cards WHERE id = ?', (card_id,))
            row = cursor.fetchone()
            conn.close()
            
            if row:
                abilities = json.loads(row[9]) if row[9] else []
                return Card(
                    id=row[0], name=row[1], cost=row[2], card_type=row[3],
                    rarity=row[4], set_name=row[5], description=row[6],
                    attack=row[7], health=row[8], abilities=abilities
                )
            return None
        except Exception as e:
            logger.error(f"Error retrieving card: {e}")
            return None
    
    def search_cards(self, **filters) -> List[Card]:
        """Search cards with filters"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            query = "SELECT * FROM cards WHERE 1=1"
            params = []
            
            if 'name' in filters:
                query += " AND name LIKE ?"
                params.append(f"%{filters['name']}%")
            
            if 'card_type' in filters:
                query += " AND card_type = ?"
                params.append(filters['card_type'])
            
            if 'rarity' in filters:
                query += " AND rarity = ?"
                params.append(filters['rarity'])
            
            if 'cost' in filters:
                query += " AND cost = ?"
                params.append(filters['cost'])
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()
            
            cards = []
            for row in rows:
                abilities = json.loads(row[9]) if row[9] else []
                cards.append(Card(
                    id=row[0], name=row[1], cost=row[2], card_type=row[3],
                    rarity=row[4], set_name=row[5], description=row[6],
                    attack=row[7], health=row[8], abilities=abilities
                ))
            
            return cards
        except Exception as e:
            logger.error(f"Error searching cards: {e}")
            return []

class DeckManager:
    """Manages deck creation, modification, and analysis"""
    
    def __init__(self, db_path: str = "deckwizard.db"):
        self.db_path = db_path
        self.card_db = CardDatabase(db_path)
    
    def create_deck(self, name: str, format: str) -> Deck:
        """Create a new deck"""
        deck_id = f"deck_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        current_time = datetime.now().isoformat()
        
        deck = Deck(
            id=deck_id,
            name=name,
            format=format,
            cards={},
            created_date=current_time,
            last_modified=current_time
        )
        
        self.save_deck(deck)
        logger.info(f"Created deck: {name}")
        return deck
    
    def save_deck(self, deck: Deck) -> bool:
        """Save deck to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO decks 
                (id, name, format, cards, created_date, last_modified, win_rate, games_played)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                deck.id, deck.name, deck.format, json.dumps(deck.cards),
                deck.created_date, deck.last_modified, deck.win_rate, deck.games_played
            ))
            
            conn.commit()
            conn.close()
            logger.info(f"Saved deck: {deck.name}")
            return True
        except Exception as e:
            logger.error(f"Error saving deck: {e}")
            return False
    
    def load_deck(self, deck_id: str) -> Optional[Deck]:
        """Load deck from database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM decks WHERE id = ?', (deck_id,))
            row = cursor.fetchone()
            conn.close()
            
            if row:
                cards = json.loads(row[3]) if row[3] else {}
                return Deck(
                    id=row[0], name=row[1], format=row[2], cards=cards,
                    created_date=row[4], last_modified=row[5],
                    win_rate=row[6], games_played=row[7]
                )
            return None
        except Exception as e:
            logger.error(f"Error loading deck: {e}")
            return None
    
    def add_card_to_deck(self, deck: Deck, card_id: str, quantity: int = 1) -> bool:
        """Add cards to deck"""
        if card_id in deck.cards:
            deck.cards[card_id] += quantity
        else:
            deck.cards[card_id] = quantity
        
        deck.last_modified = datetime.now().isoformat()
        return self.save_deck(deck)
    
    def remove_card_from_deck(self, deck: Deck, card_id: str, quantity: int = 1) -> bool:
        """Remove cards from deck"""
        if card_id in deck.cards:
            deck.cards[card_id] -= quantity
            if deck.cards[card_id] <= 0:
                del deck.cards[card_id]
            
            deck.last_modified = datetime.now().isoformat()
            return self.save_deck(deck)
        return False
    
    def analyze_deck(self, deck: Deck) -> Dict:
        """Analyze deck composition and provide insights"""
        analysis = {
            'total_cards': deck.get_total_cards(),
            'mana_curve': deck.get_mana_curve(),
            'card_types': {},
            'rarities': {},
            'recommendations': []
        }
        
        # Analyze card types and rarities
        for card_id, quantity in deck.cards.items():
            card = self.card_db.get_card(card_id)
            if card:
                analysis['card_types'][card.card_type] = analysis['card_types'].get(card.card_type, 0) + quantity
                analysis['rarities'][card.rarity] = analysis['rarities'].get(card.rarity, 0) + quantity
        
        # Generate recommendations
        if analysis['total_cards'] < 30:
            analysis['recommendations'].append("Deck is below minimum size (30 cards)")
        elif analysis['total_cards'] > 60:
            analysis['recommendations'].append("Deck is above recommended size (60 cards)")
        
        # Mana curve analysis
        curve = analysis['mana_curve']
        if sum(curve.get(i, 0) for i in range(1, 4)) < analysis['total_cards'] * 0.3:
            analysis['recommendations'].append("Consider adding more low-cost cards for early game")
        
        return analysis
    
    def suggest_cards(self, deck: Deck, count: int = 5) -> List[Card]:
        """Suggest cards that might fit well in the deck"""
        # Simple suggestion based on existing card types
        existing_types = set()
        for card_id in deck.cards:
            card = self.card_db.get_card(card_id)
            if card:
                existing_types.add(card.card_type)
        
        suggestions = []
        for card_type in existing_types:
            cards = self.card_db.search_cards(card_type=card_type)
            suggestions.extend([c for c in cards if c.id not in deck.cards])
        
        return suggestions[:count]

class GameTracker:
    """Tracks game results and statistics"""
    
    def __init__(self, db_path: str = "deckwizard.db"):
        self.db_path = db_path
    
    def record_game(self, deck_id: str, opponent_deck: str, result: str, 
                   game_length: int, notes: str = "") -> bool:
        """Record a game result"""
        try:
            game_id = f"game_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            game_result = GameResult(
                id=game_id,
                deck_id=deck_id,
                opponent_deck=opponent_deck,
                result=result,
                game_length=game_length,
                date_played=datetime.now().isoformat(),
                notes=notes
            )
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO game_results 
                (id, deck_id, opponent_deck, result, game_length, date_played, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                game_result.id, game_result.deck_id, game_result.opponent_deck,
                game_result.result, game_result.game_length, game_result.date_played,
                game_result.notes
            ))
            
            # Update deck statistics
            cursor.execute('''
                SELECT games_played, win_rate FROM decks WHERE id = ?
            ''', (deck_id,))
            
            row = cursor.fetchone()
            if row:
                games_played = row[0] + 1
                current_wins = row[1] * row[0]
                new_wins = current_wins + (1 if result == 'win' else 0)
                new_win_rate = new_wins / games_played
                
                cursor.execute('''
                    UPDATE decks SET games_played = ?, win_rate = ? WHERE id = ?
                ''', (games_played, new_win_rate, deck_id))
            
            conn.commit()
            conn.close()
            logger.info(f"Recorded game result: {result}")
            return True
        except Exception as e:
            logger.error(f"Error recording game: {e}")
            return False
    
    def get_deck_statistics(self, deck_id: str) -> Dict:
        """Get comprehensive statistics for a deck"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get basic deck stats
            cursor.execute('''
                SELECT games_played, win_rate FROM decks WHERE id = ?
            ''', (deck_id,))
            deck_row = cursor.fetchone()
            
            # Get game results
            cursor.execute('''
                SELECT result, game_length, date_played FROM game_results 
                WHERE deck_id = ? ORDER BY date_played DESC
            ''', (deck_id,))
            games = cursor.fetchall()
            
            conn.close()
            
            if not deck_row:
                return {}
            
            stats = {
                'games_played': deck_row[0],
                'win_rate': deck_row[1],
                'wins': sum(1 for g in games if g[0] == 'win'),
                'losses': sum(1 for g in games if g[0] == 'loss'),
                'draws': sum(1 for g in games if g[0] == 'draw'),
                'average_game_length': sum(g[1] for g in games) / len(games) if games else 0,
                'recent_games': games[:10]  # Last 10 games
            }
            
            return stats
        except Exception as e:
            logger.error(f"Error getting deck statistics: {e}")
            return {}

class DeckWizardCLI:
    """Command-line interface for DeckWizard"""
    
    def __init__(self):
        self.card_db = CardDatabase()
        self.deck_manager = DeckManager()
        self.game_tracker = GameTracker()
    
    def run(self):
        """Main CLI loop"""
        parser = argparse.ArgumentParser(description="DeckWizard - Advanced Card Game Management Suite")
        subparsers = parser.add_subparsers(dest='command', help='Available commands')
        
        # Card management commands
        card_parser = subparsers.add_parser('card', help='Card management')
        card_subparsers = card_parser.add_subparsers(dest='card_action')
        
        add_card_parser = card_subparsers.add_parser('add', help='Add a card')
        add_card_parser.add_argument('--name', required=True, help='Card name')
        add_card_parser.add_argument('--cost', type=int, required=True, help='Mana cost')
        add_card_parser.add_argument('--type', required=True, help='Card type')
        add_card_parser.add_argument('--rarity', required=True, help='Card rarity')
        add_card_parser.add_argument('--set', required=True, help='Set name')
        add_card_parser.add_argument('--description', help='Card description')
        add_card_parser.add_argument('--attack', type=int, help='Attack value')
        add_card_parser.add_argument('--health', type=int, help='Health value')
        
        search_card_parser = card_subparsers.add_parser('search', help='Search cards')
        search_card_parser.add_argument('--name', help='Card name')
        search_card_parser.add_argument('--type', help='Card type')
        search_card_parser.add_argument('--rarity', help='Card rarity')
        search_card_parser.add_argument('--cost', type=int, help='Mana cost')
        
        # Deck management commands
        deck_parser = subparsers.add_parser('deck', help='Deck management')
        deck_subparsers = deck_parser.add_subparsers(dest='deck_action')
        
        create_deck_parser = deck_subparsers.add_parser('create', help='Create a deck')
        create_deck_parser.add_argument('--name', required=True, help='Deck name')
        create_deck_parser.add_argument('--format', required=True, help='Game format')
        
        analyze_deck_parser = deck_subparsers.add_parser('analyze', help='Analyze a deck')
        analyze_deck_parser.add_argument('--id', required=True, help='Deck ID')
        
        # Game tracking commands
        game_parser = subparsers.add_parser('game', help='Game tracking')
        game_subparsers = game_parser.add_subparsers(dest='game_action')
        
        record_game_parser = game_subparsers.add_parser('record', help='Record a game')
        record_game_parser.add_argument('--deck-id', required=True, help='Deck ID')
        record_game_parser.add_argument('--opponent', required=True, help='Opponent deck')
        record_game_parser.add_argument('--result', required=True, choices=['win', 'loss', 'draw'])
        record_game_parser.add_argument('--length', type=int, required=True, help='Game length in turns')
        record_game_parser.add_argument('--notes', help='Game notes')
        
        stats_parser = game_subparsers.add_parser('stats', help='View deck statistics')
        stats_parser.add_argument('--deck-id', required=True, help='Deck ID')
        
        # Demo command
        demo_parser = subparsers.add_parser('demo', help='Run demo with sample data')
        
        args = parser.parse_args()
        
        if args.command == 'card':
            self.handle_card_command(args)
        elif args.command == 'deck':
            self.handle_deck_command(args)
        elif args.command == 'game':
            self.handle_game_command(args)
        elif args.command == 'demo':
            self.run_demo()
        else:
            parser.print_help()
    
    def handle_card_command(self, args):
        """Handle card-related commands"""
        if args.card_action == 'add':
            card_id = f"card_{args.name.lower().replace(' ', '_')}"
            card = Card(
                id=card_id,
                name=args.name,
                cost=args.cost,
                card_type=args.type,
                rarity=args.rarity,
                set_name=args.set,
                description=args.description or "",
                attack=args.attack,
                health=args.health
            )
            
            if self.card_db.add_card(card):
                print(f"✅ Added card: {args.name}")
            else:
                print(f"❌ Failed to add card: {args.name}")
        
        elif args.card_action == 'search':
            filters = {}
            if args.name:
                filters['name'] = args.name
            if args.type:
                filters['card_type'] = args.type
            if args.rarity:
                filters['rarity'] = args.rarity
            if args.cost is not None:
                filters['cost'] = args.cost
            
            cards = self.card_db.search_cards(**filters)
            
            if cards:
                print(f"\n🔍 Found {len(cards)} cards:")
                for card in cards:
                    print(f"  • {card.name} ({card.cost}) - {card.card_type} - {card.rarity}")
            else:
                print("No cards found matching the criteria.")
    
    def handle_deck_command(self, args):
        """Handle deck-related commands"""
        if args.deck_action == 'create':
            deck = self.deck_manager.create_deck(args.name, args.format)
            print(f"✅ Created deck: {args.name} (ID: {deck.id})")
        
        elif args.deck_action == 'analyze':
            deck = self.deck_manager.load_deck(args.id)
            if deck:
                analysis = self.deck_manager.analyze_deck(deck)
                print(f"\n📊 Analysis for deck: {deck.name}")
                print(f"Total cards: {analysis['total_cards']}")
                print(f"Mana curve: {analysis['mana_curve']}")
                print(f"Card types: {analysis['card_types']}")
                print(f"Rarities: {analysis['rarities']}")
                
                if analysis['recommendations']:
                    print("\n💡 Recommendations:")
                    for rec in analysis['recommendations']:
                        print(f"  • {rec}")
            else:
                print(f"❌ Deck not found: {args.id}")
    
    def handle_game_command(self, args):
        """Handle game-related commands"""
        if args.game_action == 'record':
            if self.game_tracker.record_game(
                args.deck_id, args.opponent, args.result, 
                args.length, args.notes or ""
            ):
                print(f"✅ Recorded game: {args.result}")
            else:
                print("❌ Failed to record game")
        
        elif args.game_action == 'stats':
            stats = self.game_tracker.get_deck_statistics(args.deck_id)
            if stats:
                print(f"\n📈 Statistics for deck: {args.deck_id}")
                print(f"Games played: {stats['games_played']}")
                print(f"Win rate: {stats['win_rate']:.1%}")
                print(f"Wins: {stats['wins']}, Losses: {stats['losses']}, Draws: {stats['draws']}")
                print(f"Average game length: {stats['average_game_length']:.1f} turns")
            else:
                print(f"❌ No statistics found for deck: {args.deck_id}")
    
    def run_demo(self):
        """Run a demonstration with sample data"""
        print("🎮 Running DeckWizard Demo...")
        
        # Add sample cards
        sample_cards = [
            Card("fire_bolt", "Fire Bolt", 1, "Spell", "Common", "Core Set", "Deal 3 damage"),
            Card("lightning_strike", "Lightning Strike", 2, "Spell", "Common", "Core Set", "Deal 4 damage"),
            Card("goblin_warrior", "Goblin Warrior", 1, "Creature", "Common", "Core Set", "A fierce warrior", 2, 1),
            Card("dragon_lord", "Dragon Lord", 8, "Creature", "Legendary", "Core Set", "Flying, powerful", 8, 8),
            Card("healing_potion", "Healing Potion", 2, "Spell", "Common", "Core Set", "Restore 5 health")
        ]
        
        for card in sample_cards:
            self.card_db.add_card(card)
        
        print("✅ Added sample cards")
        
        # Create a sample deck
        deck = self.deck_manager.create_deck("Fire Deck", "Standard")
        self.deck_manager.add_card_to_deck(deck, "fire_bolt", 4)
        self.deck_manager.add_card_to_deck(deck, "lightning_strike", 3)
        self.deck_manager.add_card_to_deck(deck, "goblin_warrior", 4)
        self.deck_manager.add_card_to_deck(deck, "dragon_lord", 1)
        self.deck_manager.add_card_to_deck(deck, "healing_potion", 2)
        
        print(f"✅ Created sample deck: {deck.name}")
        
        # Record some sample games
        results = ['win', 'win', 'loss', 'win', 'draw']
        for i, result in enumerate(results):
            self.game_tracker.record_game(
                deck.id, f"Opponent Deck {i+1}", result, 
                random.randint(5, 15), f"Game {i+1} notes"
            )
        
        print("✅ Recorded sample games")
        
        # Show analysis
        analysis = self.deck_manager.analyze_deck(deck)
        stats = self.game_tracker.get_deck_statistics(deck.id)
        
        print(f"\n📊 Demo Results:")
        print(f"Deck: {deck.name}")
        print(f"Total cards: {analysis['total_cards']}")
        print(f"Games played: {stats['games_played']}")
        print(f"Win rate: {stats['win_rate']:.1%}")
        
        print(f"\n🎉 Demo completed! Deck ID: {deck.id}")
        print("Try: python deckwizard.py deck analyze --id", deck.id)

if __name__ == "__main__":
    cli = DeckWizardCLI()
    cli.run()

