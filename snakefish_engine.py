"""
Snakefish Chess Engine Integration
All snakefish files are at root level
"""

import sys
import os

print("🔍 Initializing Snakefish Engine...")

# Snakefish files should be in the same directory
current_dir = os.path.dirname(os.path.abspath(__file__))

# List all .py files in current directory
print(f"\n📁 Files in {current_dir}:")
for file in os.listdir(current_dir):
    if file.endswith('.py'):
        print(f"  - {file}")

try:
    # Try to import snakefish modules from current directory
    import bitboard
    import constants
    import evaluation
    import game
    import move
    import movegen
    import search
    import square
    import tables
    
    # Import Chessboard - check if it's available
    try:
        from chessboard import Chessboard
        print("✅ Chessboard imported successfully")
        CHESSBOARD_IMPORTED = True
    except ImportError as e:
        print(f"⚠️ Could not import Chessboard: {e}")
        CHESSBOARD_IMPORTED = False
    
    # If all imports succeed
    SNAKEFISH_AVAILABLE = CHESSBOARD_IMPORTED
    if SNAKEFISH_AVAILABLE:
        print("✅ All snakefish modules imported successfully!")
    else:
        print("⚠️ Chessboard module missing")
        
except ImportError as e:
    print(f"❌ Snakefish import error: {e}")
    SNAKEFISH_AVAILABLE = False


class SnakefishEngine:
    """Wrapper for Snakefish chess engine"""
    
    def __init__(self, difficulty=3):
        self.difficulty = difficulty
        
        # Map difficulty to search depth
        difficulty_map = {
            1: 1,  # Easy: depth 1
            2: 2,  # Medium: depth 2
            3: 3,  # Hard: depth 3
            4: 4   # Expert: depth 4
        }
        
        self.search_depth = difficulty_map.get(difficulty, 2)
        self.engine = None
        
        if SNAKEFISH_AVAILABLE:
            if self.initialize_engine():
                print(f"🎯 Snakefish engine initialized with difficulty {difficulty}")
            else:
                print("⚠️ Failed to initialize snakefish engine, using fallback")
        else:
            print("⚠️ Snakefish not available, using fallback engine")
    
    def initialize_engine(self):
        """Initialize the snakefish engine"""
        try:
            # Create a new chessboard with starting position
            self.engine = Chessboard()
            self.engine.set_fen("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
            print("✅ Snakefish chessboard initialized")
            return True
        except Exception as e:
            print(f"❌ Failed to initialize snakefish chessboard: {e}")
            return False
    
    def get_best_move(self, fen):
        """Get the best move using snakefish engine"""
        if not SNAKEFISH_AVAILABLE or not self.engine:
            print("⚠️ Snakefish not available, using python-chess fallback")
            return self.get_fallback_move(fen)
        
        try:
            print(f"\n🤖 Snakefish thinking (depth: {self.search_depth})...")
            
            # Set position
            if not self.set_position_from_fen(fen):
                return self.get_fallback_move(fen)
            
            # Create search object
            search_obj = search.Search(self.engine)
            
            # Set search parameters
            search_obj.set_depth(self.search_depth)
            
            # Get best move
            print("🔍 Searching for best move...")
            best_move = search_obj.get_best_move()
            
            if not best_move:
                print("⚠️ No best move found")
                return self.get_fallback_move(fen)
            
            # Convert snakefish move to standard notation
            from_sq = best_move.get_from_square()
            to_sq = best_move.get_to_square()
            promotion = best_move.get_promotion()
            
            # Convert square indices to algebraic notation
            from_algebraic = self.square_to_algebraic(from_sq)
            to_algebraic = self.square_to_algebraic(to_sq)
            
            # Map promotion piece
            promotion_map = {
                1: 'n',  # Knight
                2: 'b',  # Bishop
                3: 'r',  # Rook
                4: 'q'   # Queen
            }
            
            promotion_char = promotion_map.get(promotion)
            
            print(f"✅ Snakefish move: {from_algebraic} -> {to_algebraic}")
            return from_algebraic, to_algebraic, promotion_char
            
        except Exception as e:
            print(f"❌ Error in snakefish engine: {e}")
            return self.get_fallback_move(fen)
    
    def set_position_from_fen(self, fen):
        """Set board position from FEN string"""
        try:
            # Complete the FEN if needed
            fen_parts = fen.split()
            if len(fen_parts) < 2:
                fen += " w - - 0 1"
            elif len(fen_parts) < 5:
                fen = fen_parts[0] + " " + fen_parts[1] + " - - 0 1"
            
            self.engine.set_fen(fen)
            return True
        except Exception as e:
            print(f"❌ Error setting FEN: {e}")
            return False
    
    def square_to_algebraic(self, square_index):
        """Convert square index (0-63) to algebraic notation (a1-h8)"""
        if square_index < 0 or square_index > 63:
            return ""
        
        files = 'abcdefgh'
        ranks = '12345678'
        
        file_idx = square_index % 8
        rank_idx = square_index // 8
        
        return files[file_idx] + ranks[7 - rank_idx]
    
    def get_fallback_move(self, fen):
        """Fallback to python-chess if snakefish fails"""
        try:
            import chess
            import random
            
            board = chess.Board(fen)
            
            if board.is_game_over():
                return None, None, None
            
            # Simple evaluation for fallback
            moves = list(board.legal_moves)
            
            if self.difficulty == 1:
                # Easy: random move
                move = random.choice(moves)
            else:
                # Better: prioritize captures and checks
                scored_moves = []
                for move in moves:
                    score = 0
                    
                    # Captures are good
                    if board.is_capture(move):
                        captured = board.piece_at(move.to_square)
                        if captured:
                            piece_values = {
                                chess.PAWN: 1,
                                chess.KNIGHT: 3,
                                chess.BISHOP: 3,
                                chess.ROOK: 5,
                                chess.QUEEN: 9
                            }
                            score += piece_values.get(captured.piece_type, 0) * 10
                    
                    # Checks are good
                    board.push(move)
                    if board.is_check():
                        score += 5
                    board.pop()
                    
                    scored_moves.append((score, move))
                
                scored_moves.sort(reverse=True)
                move = scored_moves[0][1]
            
            from_sq = chess.square_name(move.from_square)
            to_sq = chess.square_name(move.to_square)
            promotion = chess.piece_symbol(move.promotion).lower() if move.promotion else None
            
            print(f"🔄 Fallback move: {from_sq} -> {to_sq}")
            return from_sq, to_sq, promotion
            
        except Exception as e:
            print(f"❌ Fallback engine also failed: {e}")
            return None, None, None


class SimpleEngine:
    """Simple chess engine as fallback"""
    
    def __init__(self, difficulty=2):
        self.difficulty = difficulty
    
    def get_best_move(self, fen):
        """Get a move using python-chess"""
        try:
            import chess
            import random
            
            board = chess.Board(fen)
            
            if board.is_game_over():
                return None, None, None
            
            moves = list(board.legal_moves)
            
            if self.difficulty == 1:
                move = random.choice(moves)
            else:
                scored_moves = []
                for move in moves:
                    score = 0
                    
                    if board.is_capture(move):
                        captured = board.piece_at(move.to_square)
                        if captured:
                            piece_values = {
                                chess.PAWN: 1,
                                chess.KNIGHT: 3,
                                chess.BISHOP: 3,
                                chess.ROOK: 5,
                                chess.QUEEN: 9
                            }
                            score += piece_values.get(captured.piece_type, 0) * 10
                    
                    board.push(move)
                    if board.is_check():
                        score += 5
                    board.pop()
                    
                    scored_moves.append((score, move))
                
                scored_moves.sort(reverse=True)
                move = scored_moves[0][1]
            
            from_sq = chess.square_name(move.from_square)
            to_sq = chess.square_name(move.to_square)
            promotion = chess.piece_symbol(move.promotion).lower() if move.promotion else None
            
            return from_sq, to_sq, promotion
            
        except Exception as e:
            print(f"Simple engine error: {e}")
            return None, None, None


# Test the engine
if __name__ == "__main__":
    print("\n🧪 Testing Chess Engine...")
    
    # Test with starting position
    engine = SnakefishEngine(difficulty=2)
    
    test_fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    print(f"\nTesting with FEN: {test_fen}")
    
    result = engine.get_best_move(test_fen)
    if result[0]:
        print(f"✅ Engine move: {result[0]} -> {result[1]}")
    else:
        print("❌ Engine failed to find a move")