from flask import Flask, render_template, jsonify, request
import chess
import os
import random
import traceback

# Try to import ML model
try:
    from chess_ml_model import ChessMLModel
    ML_AVAILABLE = True
    print("✅ ML Model import successful")
except ImportError as e:
    print(f"⚠️  ML Model import failed: {e}")
    print("   Running with traditional engine only")
    ML_AVAILABLE = False

from strong_engine import StrongChessEngine

app = Flask(__name__)

# Initialize engines
chess_engine = StrongChessEngine(difficulty=3)
ml_engine = ChessMLModel() if ML_AVAILABLE else None

# ------------------------------------------------------------
# Opening book – personalized for your style
# Use normalized FEN (without move counters) as keys
# ------------------------------------------------------------
def normalize_fen(fen: str) -> str:
    """Strip halfmove clock and fullmove number from FEN."""
    return ' '.join(fen.split(' ')[:4])

OPENING_BOOK = {
    # White: Queen's Gambit
    normalize_fen("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"): ["d2d4"],
    normalize_fen("rnbqkbnr/ppp1pppp/8/3p4/3P4/8/PPP1PPPP/RNBQKBNR w KQkq - 0 2"): ["c2c4"],
    # After 1.d4 Nf6 (Indian)
    normalize_fen("rnbqkb1r/pppppppp/5n2/8/3P4/8/PPP1PPPP/RNBQKBNR w KQkq - 1 2"): ["c2c4"],
    # After 1.d4 e6
    normalize_fen("rnbqkbnr/pppp1ppp/4p3/8/3P4/8/PPP1PPPP/RNBQKBNR w KQkq - 0 2"): ["c2c4"],
    # Black: French Defence
    normalize_fen("rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1"): ["e7e6"],
    # After 1.e4 e6 2.d4 d5 – engine chooses best continuation (empty list)
    normalize_fen("rnbqkbnr/ppp1pppp/4p3/3p4/3PP3/8/PPP2PPP/RNBQKBNR w KQkq - 0 3"): [],
}

def get_opening_book_move(fen: str) -> chess.Move | None:
    """Return a move from the opening book if available, else None."""
    norm_fen = normalize_fen(fen)
    if norm_fen in OPENING_BOOK and OPENING_BOOK[norm_fen]:
        move_uci = random.choice(OPENING_BOOK[norm_fen])
        print(f"📖 Book move found for normalized FEN: {norm_fen} -> {move_uci}")
        return chess.Move.from_uci(move_uci)
    return None

# ------------------------------------------------------------
# Game phase detection (fine‑tuned thresholds)
# ------------------------------------------------------------
def get_game_phase(fen: str) -> str:
    """Return 'opening', 'middlegame', or 'endgame' based on material."""
    board = chess.Board(fen)
    piece_values = {chess.PAWN: 100, chess.KNIGHT: 320, chess.BISHOP: 330,
                    chess.ROOK: 500, chess.QUEEN: 900}
    total = 0
    for square in chess.SQUARES:
        piece = board.piece_at(square)
        if piece and piece.piece_type != chess.KING:
            total += piece_values[piece.piece_type]
    if total > 4500:
        return 'opening'
    elif total > 1500:
        return 'middlegame'
    else:
        return 'endgame'

# ------------------------------------------------------------
# Position complexity (for dynamic depth)
# ------------------------------------------------------------
def position_complexity(fen: str) -> int:
    """Estimate tactical complexity based on number of attacks."""
    board = chess.Board(fen)
    attacks = 0
    for square in chess.SQUARES:
        if board.piece_at(square):
            attacks += len(board.attacks(square))
    return attacks

# ------------------------------------------------------------
# Flask routes
# ------------------------------------------------------------
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_bot_move', methods=['POST'])
def get_bot_move():
    data = request.json
    fen = data.get('fen')
    difficulty = data.get('difficulty', 3)
    use_ml = data.get('use_ml', False)

    try:
        chess_engine.difficulty = difficulty
        chess_engine.update_depth()

        if use_ml and ml_engine and ml_engine.is_loaded():
            original_use_ml = chess_engine.use_ml
            chess_engine.use_ml = True
            from_sq, to_sq, promotion = chess_engine.get_best_move(fen)
            chess_engine.use_ml = original_use_ml
            engine_type = 'ml_enhanced'
        else:
            from_sq, to_sq, promotion = chess_engine.get_best_move(fen)
            engine_type = 'traditional'

        if from_sq and to_sq:
            return jsonify({
                'from_square': from_sq,
                'to_square': to_sq,
                'promotion': promotion,
                'engine_type': engine_type
            })
        else:
            board = chess.Board(fen)
            if board.is_game_over():
                return jsonify({'error': 'Game is over'}), 400
            move = random.choice(list(board.legal_moves))
            return jsonify({
                'from_square': chess.square_name(move.from_square),
                'to_square': chess.square_name(move.to_square),
                'promotion': chess.piece_symbol(move.promotion).lower() if move.promotion else None,
                'engine_type': 'random_fallback'
            })
    except Exception as e:
        print(f"Error in get_bot_move: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 400

@app.route('/get_ml_move', methods=['POST'])
def get_ml_move():
    if not ml_engine or not ml_engine.is_loaded():
        return jsonify({'error': 'ML model not available'}), 400

    data = request.json
    fen = data.get('fen')
    search_depth = data.get('depth', 1)

    try:
        board = chess.Board(fen)
        if board.is_game_over():
            return jsonify({'error': 'Game is over'}), 400

        legal_moves = list(board.legal_moves)
        if not legal_moves:
            return jsonify({'error': 'No legal moves'}), 400

        best_move = None
        best_eval = -float('inf') if board.turn == chess.WHITE else float('inf')

        for move in legal_moves:
            board_copy = board.copy()
            board_copy.push(move)
            eval_score = float(ml_engine.evaluate_position(board_copy.fen()))

            if board.turn == chess.WHITE:
                if eval_score > best_eval:
                    best_eval = eval_score
                    best_move = move
            else:
                if eval_score < best_eval:
                    best_eval = eval_score
                    best_move = move

        if best_move:
            return jsonify({
                'from_square': chess.square_name(best_move.from_square),
                'to_square': chess.square_name(best_move.to_square),
                'promotion': chess.piece_symbol(best_move.promotion).lower() if best_move.promotion else None,
                'eval': float(best_eval),
                'engine_type': 'ml_direct',
                'search_depth': search_depth
            })
        else:
            move = random.choice(legal_moves)
            return jsonify({
                'from_square': chess.square_name(move.from_square),
                'to_square': chess.square_name(move.to_square),
                'promotion': chess.piece_symbol(move.promotion).lower() if move.promotion else None,
                'engine_type': 'ml_random_fallback'
            })
    except Exception as e:
        print(f"Error in get_ml_move: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 400

@app.route('/get_hybrid_move', methods=['POST'])
def get_hybrid_move():
    data = request.json
    fen = data.get('fen')
    difficulty = data.get('difficulty', 3)
    ml_weight = data.get('ml_weight', 0.7)

    try:
        # First, check if we're in the opening phase and have a book move
        phase = get_game_phase(fen)
        if phase == 'opening':
            board = chess.Board(fen)
            if not board.is_game_over():
                book_move = get_opening_book_move(fen)
                if book_move and book_move in board.legal_moves:
                    from_sq = chess.square_name(book_move.from_square)
                    to_sq = chess.square_name(book_move.to_square)
                    promotion = chess.piece_symbol(book_move.promotion).lower() if book_move.promotion else None
                    print(f"  📖 Opening book move (hybrid): {from_sq} -> {to_sq}")
                    return jsonify({
                        'from_square': from_sq,
                        'to_square': to_sq,
                        'promotion': promotion,
                        'engine_type': 'opening_book_hybrid',
                        'ml_weight': ml_weight
                    })

        # If no book move, proceed with hybrid engine
        chess_engine.difficulty = difficulty
        chess_engine.update_depth()

        original_use_ml = chess_engine.use_ml
        original_ml_model = chess_engine.ml_model

        if ml_engine and ml_engine.is_loaded():
            chess_engine.use_ml = True
            chess_engine.ml_model = ml_engine
            print(f"Using hybrid engine (ML weight: {ml_weight})")

        from_sq, to_sq, promotion = chess_engine.get_best_move(fen)

        chess_engine.use_ml = original_use_ml
        chess_engine.ml_model = original_ml_model

        if from_sq and to_sq:
            return jsonify({
                'from_square': from_sq,
                'to_square': to_sq,
                'promotion': promotion,
                'engine_type': 'hybrid',
                'ml_weight': ml_weight
            })
        else:
            board = chess.Board(fen)
            if board.is_game_over():
                return jsonify({'error': 'Game is over'}), 400
            move = random.choice(list(board.legal_moves))
            return jsonify({
                'from_square': chess.square_name(move.from_square),
                'to_square': chess.square_name(move.to_square),
                'promotion': chess.piece_symbol(move.promotion).lower() if move.promotion else None,
                'engine_type': 'random_fallback'
            })
    except Exception as e:
        print(f"Error in get_hybrid_move: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 400

@app.route('/get_engine_info', methods=['GET'])
def get_engine_info():
    engines = {
        'traditional': True,
        'ml': ML_AVAILABLE and ml_engine and ml_engine.is_loaded(),
        'hybrid': ML_AVAILABLE and ml_engine and ml_engine.is_loaded()
    }

    ml_info = None
    if ml_engine and ml_engine.is_loaded():
        ml_info = {
            'loaded': True,
            'load_time': getattr(ml_engine, 'load_time', None),
            'model_type': 'PyTorch CNN',
            'trained_positions': '16.5M',
            'mae': '~80-100cp',
            'architecture': '4.9M parameters, residual CNN'
        }
    else:
        ml_info = {'loaded': False}

    return jsonify({
        'engines': engines,
        'ml': ml_info,
        'traditional_engine': {
            'difficulty_levels': 4,
            'current_difficulty': chess_engine.difficulty
        }
    })

@app.route('/get_legal_moves', methods=['POST'])
def get_legal_moves():
    data = request.json
    fen = data.get('fen')
    square = data.get('square')

    try:
        board = chess.Board(fen)
        moves = []

        if square:
            from_square = chess.parse_square(square)
            for move in board.legal_moves:
                if move.from_square == from_square:
                    moves.append(chess.square_name(move.to_square))
        else:
            for move in board.legal_moves:
                moves.append(chess.square_name(move.to_square))

        return jsonify({'legal_moves': moves})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/get_adaptive_move', methods=['POST'])
def get_adaptive_move():
    data = request.json
    fen = data.get('fen')
    difficulty = data.get('difficulty', 3)

    phase = get_game_phase(fen)
    print(f"Game phase: {phase}")

    try:
        # First, try opening book if in opening phase
        if phase == 'opening':
            board = chess.Board(fen)
            if board.is_game_over():
                return jsonify({'error': 'Game is over'}), 400

            book_move = get_opening_book_move(fen)
            if book_move and book_move in board.legal_moves:
                from_sq = chess.square_name(book_move.from_square)
                to_sq = chess.square_name(book_move.to_square)
                promotion = chess.piece_symbol(book_move.promotion).lower() if book_move.promotion else None
                print(f"  📖 Opening book move: {from_sq} -> {to_sq}")
                return jsonify({
                    'from_square': from_sq,
                    'to_square': to_sq,
                    'promotion': promotion,
                    'engine_type': 'opening_book',
                    'phase': phase,
                    'depth': 1
                })

        # Otherwise proceed with phase‑appropriate engine
        if phase == 'opening':
            # Pure ML (1‑ply)
            if not ml_engine or not ml_engine.is_loaded():
                return jsonify({'error': 'ML model not available'}), 400

            board = chess.Board(fen)
            legal_moves = list(board.legal_moves)
            if not legal_moves:
                return jsonify({'error': 'No legal moves'}), 400

            best_move = None
            best_eval = -float('inf') if board.turn == chess.WHITE else float('inf')
            for move in legal_moves:
                board_copy = board.copy()
                board_copy.push(move)
                eval_score = float(ml_engine.evaluate_position(board_copy.fen()))
                if board.turn == chess.WHITE:
                    if eval_score > best_eval:
                        best_eval = eval_score
                        best_move = move
                else:
                    if eval_score < best_eval:
                        best_eval = eval_score
                        best_move = move

            if best_move:
                from_sq = chess.square_name(best_move.from_square)
                to_sq = chess.square_name(best_move.to_square)
                promotion = chess.piece_symbol(best_move.promotion).lower() if best_move.promotion else None
                engine_type = 'ml_opening'
            else:
                best_move = random.choice(legal_moves)
                from_sq = chess.square_name(best_move.from_square)
                to_sq = chess.square_name(best_move.to_square)
                promotion = chess.piece_symbol(best_move.promotion).lower() if best_move.promotion else None
                engine_type = 'ml_random_fallback'

        elif phase == 'middlegame':
            # Hybrid engine with depth adapted to complexity
            chess_engine.difficulty = difficulty
            chess_engine.update_depth()

            # Store original settings
            orig_use_ml = chess_engine.use_ml
            orig_ml_model = chess_engine.ml_model
            orig_target = chess_engine.target_depth
            orig_futility = chess_engine.futility_margin_base
            orig_rev_futility = chess_engine.reverse_futility_margin_base
            orig_null = chess_engine.null_move_reduction
            orig_asp = chess_engine.aspiration_window

            # Determine depth based on complexity
            complexity = position_complexity(fen)
            if complexity > 100:          # very tactical
                target = 4
                print(f"  ⚔️ Very tactical – depth 4")
            elif complexity > 60:          # moderately tactical
                target = 5
            else:                           # quiet
                target = 6
                print(f"  🧘 Quiet position – depth 6")

            chess_engine.target_depth = target
            chess_engine.futility_margin_base = 400
            chess_engine.reverse_futility_margin_base = 400
            chess_engine.null_move_reduction = 3
            chess_engine.aspiration_window = 100

            if ml_engine and ml_engine.is_loaded():
                chess_engine.use_ml = True
                chess_engine.ml_model = ml_engine

            from_sq, to_sq, promotion = chess_engine.get_best_move(fen)
            engine_type = f'hybrid_middlegame_depth{target}'

            # Restore
            chess_engine.use_ml = orig_use_ml
            chess_engine.ml_model = orig_ml_model
            chess_engine.target_depth = orig_target
            chess_engine.futility_margin_base = orig_futility
            chess_engine.reverse_futility_margin_base = orig_rev_futility
            chess_engine.null_move_reduction = orig_null
            chess_engine.aspiration_window = orig_asp

        else:  # endgame
            # Traditional engine, deeper and more accurate
            chess_engine.difficulty = difficulty
            chess_engine.update_depth()

            orig_use_ml = chess_engine.use_ml
            orig_target = chess_engine.target_depth
            orig_futility = chess_engine.futility_margin_base
            orig_rev_futility = chess_engine.reverse_futility_margin_base
            orig_null = chess_engine.null_move_reduction
            orig_asp = chess_engine.aspiration_window

            # Go deeper, prune less
            chess_engine.target_depth = orig_target + 2
            chess_engine.futility_margin_base = 200
            chess_engine.reverse_futility_margin_base = 200
            chess_engine.null_move_reduction = 1
            chess_engine.aspiration_window = 50
            chess_engine.use_ml = False

            from_sq, to_sq, promotion = chess_engine.get_best_move(fen)
            engine_type = f'traditional_endgame_depth{chess_engine.target_depth}'

            # Restore
            chess_engine.use_ml = orig_use_ml
            chess_engine.target_depth = orig_target
            chess_engine.futility_margin_base = orig_futility
            chess_engine.reverse_futility_margin_base = orig_rev_futility
            chess_engine.null_move_reduction = orig_null
            chess_engine.aspiration_window = orig_asp

        if from_sq and to_sq:
            return jsonify({
                'from_square': from_sq,
                'to_square': to_sq,
                'promotion': promotion,
                'engine_type': engine_type,
                'phase': phase,
                'depth': chess_engine.target_depth if phase != 'opening' else 1
            })
        else:
            # Ultimate fallback: random move
            board = chess.Board(fen)
            if board.is_game_over():
                return jsonify({'error': 'Game is over'}), 400
            move = random.choice(list(board.legal_moves))
            return jsonify({
                'from_square': chess.square_name(move.from_square),
                'to_square': chess.square_name(move.to_square),
                'promotion': chess.piece_symbol(move.promotion).lower() if move.promotion else None,
                'engine_type': 'random_fallback',
                'phase': phase
            })

    except Exception as e:
        print(f"Error in adaptive move: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 400

@app.route('/validate_move', methods=['POST'])
def validate_move():
    data = request.json
    fen = data.get('fen')
    from_sq = data.get('from')
    to_sq = data.get('to')
    promotion = data.get('promotion')

    try:
        board = chess.Board(fen)

        piece = board.piece_at(chess.parse_square(from_sq))
        is_pawn = piece and piece.piece_type == chess.PAWN
        target_rank = chess.square_rank(chess.parse_square(to_sq))

        if is_pawn and ((piece.color == chess.WHITE and target_rank == 7) or
                       (piece.color == chess.BLACK and target_rank == 0)):
            if not promotion:
                return jsonify({
                    'valid': False,
                    'requires_promotion': True,
                    'error': 'Pawn promotion required'
                })

        move_uci = f"{from_sq}{to_sq}{promotion if promotion else ''}"
        move = chess.Move.from_uci(move_uci)

        if move in board.legal_moves:
            board.push(move)
            return jsonify({
                'valid': True,
                'fen': board.fen(),
                'check': board.is_check(),
                'checkmate': board.is_checkmate(),
                'stalemate': board.is_stalemate(),
                'draw': board.is_game_over() and not board.is_checkmate(),
                'promotion_made': promotion if promotion else None
            })
        else:
            return jsonify({'valid': False, 'error': 'Illegal move'})
    except Exception as e:
        return jsonify({'valid': False, 'error': str(e)})

if __name__ == '__main__':
    print("🚀 Starting Modern Chess Game Server...")
    print("📱 Game optimized for mobile and desktop")

    print("\n🤖 Available Engines:")
    print("  • Traditional Engine: ✅")

    if ML_AVAILABLE and ml_engine and ml_engine.is_loaded():
        print("  • ML Engine: ✅ (neural network, 16.5M positions)")
        print("  • Hybrid Engine: ✅")
    else:
        print("  • ML Engine: ❌ (not available)")
        print("  • Hybrid Engine: ❌")

    # Test the traditional engine
    test_fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    result = chess_engine.get_best_move(test_fen)
    if result[0]:
        print(f"\n✅ Traditional Engine ready: {result[0]} -> {result[1]}")
    else:
        print("⚠️ Traditional Engine test failed")

    # Test ML engine if available
    if ml_engine and ml_engine.is_loaded():
        try:
            eval_result = ml_engine.evaluate_position(test_fen)
            print(f"✅ ML Engine ready: eval = {eval_result:.0f} cp")
        except Exception as e:
            print(f"⚠️ ML Engine test failed: {e}")

    port = int(os.environ.get("PORT", 8080))
    print(f"\n🌐 Server starting on http://0.0.0.0:{port}")
    print("📝 Available endpoints:")
    print("  • GET  /                     - Web interface")
    print("  • POST /get_bot_move         - Traditional engine (optionally with ML)")
    print("  • POST /get_ml_move          - Pure ML engine")
    print("  • POST /get_hybrid_move      - Hybrid engine")
    print("  • GET  /get_engine_info      - Engine information")
    print("  • POST /get_legal_moves      - Legal moves")
    print("  • POST /validate_move        - Move validation")
    print("  • POST /get_adaptive_move    - Phase‑adaptive engine with opening book")

    app.run(debug=False, host='0.0.0.0', port=port)