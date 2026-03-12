"""
Optimized Chess Engine using python-chess with time management
Compatible with the Flask web interface
"""

import chess
import math
import random
import time
from typing import List, Tuple, Optional, Dict

class StrongChessEngine:
    """Optimized chess engine with proper search algorithm and time management"""
    
    def __init__(self, difficulty=3):
        """
        difficulty levels:
        1: Easy (depth 2-3, 5 seconds max)
        2: Medium (depth 3-4, 10 seconds max) 
        3: Hard (depth 4-5, 15 seconds max)
        4: Expert (depth 5-6, 20 seconds max)
        """
        self.difficulty = difficulty
        self.use_ml = False
        self.ml_model = None  
        
        # Piece values (centipawns)
        self.piece_values = {
            chess.PAWN: 100,
            chess.KNIGHT: 320,
            chess.BISHOP: 330,
            chess.ROOK: 500,
            chess.QUEEN: 900,
            chess.KING: 20000
        }
        
        # SEE piece values (for exchange evaluation)
        self.see_values = {
            chess.PAWN: 100,
            chess.KNIGHT: 320,
            chess.BISHOP: 330,
            chess.ROOK: 500,
            chess.QUEEN: 900,
            chess.KING: 20000
        }
        
        # Piece-square tables
        self.pawn_table = [
            0,   0,   0,   0,   0,   0,   0,   0,
            50,  50,  50,  50,  50,  50,  50,  50,
            10,  10,  20,  25,  25,  20,  10,  10,
            5,   5,  10,  20,  20,  10,   5,   5,
            0,   0,   0,  15,  15,   0,   0,   0,
            5,  -5, -10,   0,   0, -10,  -5,   5,
            5,  10,  10, -20, -20,  10,  10,   5,
            0,   0,   0,   0,   0,   0,   0,   0
        ]
        
        self.knight_table = [
            -50, -40, -30, -30, -30, -30, -40, -50,
            -40, -20,   0,   5,   5,   0, -20, -40,
            -30,   0,  10,  15,  15,  10,   0, -30,
            -30,   5,  15,  20,  20,  15,   5, -30,
            -30,   0,  15,  20,  20,  15,   0, -30,
            -30,   5,  10,  15,  15,  10,   5, -30,
            -40, -20,   0,   5,   5,   0, -20, -40,
            -50, -40, -30, -30, -30, -30, -40, -50
        ]
        
        self.bishop_table = [
            -20, -10, -10, -10, -10, -10, -10, -20,
            -10,   5,   0,   0,   0,   0,   5, -10,
            -10,  10,  10,  10,  10,  10,  10, -10,
            -10,   0,  10,  10,  10,  10,   0, -10,
            -10,   5,   5,  10,  10,   5,   5, -10,
            -10,   0,   5,  10,  10,   5,   0, -10,
            -10,   0,   0,   0,   0,   0,   0, -10,
            -20, -10, -10, -10, -10, -10, -10, -20
        ]
        
        self.rook_table = [
            0,   0,   0,   5,   5,   0,   0,   0,
            -5,   0,   0,   0,   0,   0,   0,  -5,
            -5,   0,   0,   0,   0,   0,   0,  -5,
            -5,   0,   0,   0,   0,   0,   0,  -5,
            -5,   0,   0,   0,   0,   0,   0,  -5,
            -5,   0,   0,   0,   0,   0,   0,  -5,
            5,  10,  10,  10,  10,  10,  10,   5,
            0,   0,   0,   0,   0,   0,   0,   0
        ]
        
        self.queen_table = [
            -20, -10, -10,  -5,  -5, -10, -10, -20,
            -10,   0,   5,   0,   0,   0,   0, -10,
            -10,   5,   5,   5,   5,   5,   0, -10,
            0,   0,   5,   5,   5,   5,   0,  -5,
            -5,   0,   5,   5,   5,   5,   0,  -5,
            -10,   0,   5,   5,   5,   5,   0, -10,
            -10,   0,   0,   0,   0,   0,   0, -10,
            -20, -10, -10,  -5,  -5, -10, -10, -20
        ]
        
        self.king_middle_table = [
            -30, -40, -40, -50, -50, -40, -40, -30,
            -30, -40, -40, -50, -50, -40, -40, -30,
            -30, -40, -40, -50, -50, -40, -40, -30,
            -30, -40, -40, -50, -50, -40, -40, -30,
            -20, -30, -30, -40, -40, -30, -30, -20,
            -10, -20, -20, -20, -20, -20, -20, -10,
            20,  20,   0,   0,   0,   0,  20,  20,
            20,  30,  10,   0,   0,  10,  30,  20
        ]
        
        self.king_end_table = [
            -50, -40, -30, -20, -20, -30, -40, -50,
            -30, -20, -10,   0,   0, -10, -20, -30,
            -30, -10,  20,  30,  30,  20, -10, -30,
            -30, -10,  30,  40,  40,  30, -10, -30,
            -30, -10,  30,  40,  40,  30, -10, -30,
            -30, -10,  20,  30,  30,  20, -10, -30,
            -30, -30,   0,   0,   0,   0, -30, -30,
            -50, -30, -30, -30, -30, -30, -30, -50
        ]
        
        # Initialize parameters
        self.update_depth()
        
        # Search tracking
        self.nodes_searched = 0
        self.start_time = None
        self.timeout = False
        self.best_move_found = None
        
        # Move ordering heuristics
        self.killer_moves = [[None, None] for _ in range(64)]
        self.history_table = [[0 for _ in range(64)] for _ in range(64)]
        
        # Transposition table (persistent across moves)
        self.tt: Dict[int, dict] = {}
        self.tt_max_size = 1000000  # avoid memory blow
        
        # Pawn hash table (caches pawn structure evaluation)
        self.pawn_tt: Dict[int, float] = {}
        
        # Principal variation move from previous iteration (for move ordering)
        self.pv_move = None
        
        # For null-move pruning: reduction factor (R=2) and material threshold to avoid zugzwang
        self.null_move_reduction = 2
        self.null_move_material_threshold = 1500  # skip if total material below this
        self.endgame_material_threshold = 2000    # below this, consider endgame
        
        # Aspiration window size (centipawns)
        self.aspiration_window = 50
        self.aspiration_max_widening = 5  # number of widening attempts
        
        # Futility pruning margin base (scaled by depth)
        self.futility_margin_base = 300
        
        # Reverse futility pruning margin
        self.reverse_futility_margin_base = 300
        
        print(f"🎯 Chess Engine initialized with difficulty {self.difficulty}")
        print(f"   Target: Depth {self.target_depth}, Time limit: {self.max_time}s")
    
    def update_depth(self):
        """Update search parameters based on current difficulty"""
        # Time limits per difficulty
        self.time_limits = {1: 5, 2: 10, 3: 15, 4: 20}  # seconds
        self.depth_limits = {1: 3, 2: 4, 3: 5, 4: 6, 5:7}
        
        self.max_time = self.time_limits.get(self.difficulty, 10)
        self.target_depth = self.depth_limits.get(self.difficulty, 5)
        self.max_depth = self.target_depth  # For compatibility
        self.max_nodes = 1000000  # Default high value
    
    def check_timeout(self) -> bool:
        """Check if search should timeout"""
        if self.start_time and (time.time() - self.start_time) > self.max_time:
            self.timeout = True
            return True
        return False
    
    # --------------------------------------------------------------------------
    # Evaluation with optimizations and pawn hash
    # --------------------------------------------------------------------------
    def is_passed_pawn(self, board: chess.Board, square: chess.Square, color: chess.Color) -> bool:
        """Return True if the pawn on square is a passed pawn."""
        file = chess.square_file(square)
        rank = chess.square_rank(square)
        
        if color == chess.WHITE:
            for f in [file-1, file, file+1]:
                if f < 0 or f > 7:
                    continue
                for r in range(rank+1, 8):
                    s = chess.square(f, r)
                    p = board.piece_at(s)
                    if p and p.piece_type == chess.PAWN and p.color == chess.BLACK:
                        return False
        else:
            for f in [file-1, file, file+1]:
                if f < 0 or f > 7:
                    continue
                for r in range(rank-1, -1, -1):
                    s = chess.square(f, r)
                    p = board.piece_at(s)
                    if p and p.piece_type == chess.PAWN and p.color == chess.WHITE:
                        return False
        return True
    
    def evaluate_pawn_structure(self, board: chess.Board) -> float:
        """
        Evaluate pawn structure (passed, doubled, isolated) and return score from white perspective.
        Uses pawn hash table for caching.
        """
        # Compute pawn hash key (simple xor of pawn squares and colors)
        pawn_key = 0
        for square in chess.SQUARES:
            piece = board.piece_at(square)
            if piece and piece.piece_type == chess.PAWN:
                # Mix square and color into key
                pawn_key ^= (square + 1) * (1 if piece.color == chess.WHITE else 2)
        
        if pawn_key in self.pawn_tt:
            return self.pawn_tt[pawn_key]
        
        # Collect pawn squares
        white_pawns = []
        black_pawns = []
        for square in chess.SQUARES:
            piece = board.piece_at(square)
            if piece and piece.piece_type == chess.PAWN:
                if piece.color == chess.WHITE:
                    white_pawns.append(square)
                else:
                    black_pawns.append(square)
        
        score = 0
        
        # Passed pawns
        for sq in white_pawns:
            if self.is_passed_pawn(board, sq, chess.WHITE):
                score += 50
        for sq in black_pawns:
            if self.is_passed_pawn(board, sq, chess.BLACK):
                score -= 50
        
        # Doubled & isolated pawns – count per file
        def pawn_counts(pawns):
            files = [0]*8
            for sq in pawns:
                files[chess.square_file(sq)] += 1
            return files
        
        white_files = pawn_counts(white_pawns)
        black_files = pawn_counts(black_pawns)
        
        # Doubled penalty
        doubled_w = sum(max(0, cnt-1) for cnt in white_files)
        doubled_b = sum(max(0, cnt-1) for cnt in black_files)
        score -= doubled_w * 20
        score += doubled_b * 20
        
        # Isolated penalty
        isolated_w = 0
        for f in range(8):
            if white_files[f] > 0:
                left = f>0 and white_files[f-1]>0
                right = f<7 and white_files[f+1]>0
                if not left and not right:
                    isolated_w += 1
        isolated_b = 0
        for f in range(8):
            if black_files[f] > 0:
                left = f>0 and black_files[f-1]>0
                right = f<7 and black_files[f+1]>0
                if not left and not right:
                    isolated_b += 1
        score -= isolated_w * 15
        score += isolated_b * 15
        
        self.pawn_tt[pawn_key] = score
        return score
    
    def evaluate_position(self, board: chess.Board) -> float:
        """
        Fast evaluation of the board position.
        Returns score from the perspective of the side to move.
        """
        # Quick terminal condition checks
        if board.is_checkmate():
            return -100000  # will be adjusted with ply later
        if board.is_stalemate() or board.is_insufficient_material():
            return 0
        if self.use_ml and self.ml_model is not None:
            ml_score = self.ml_model.evaluate_position(board.fen())
            ml_score if board.turn == chess.WHITE else -ml_score
            
        # Material and positional evaluation
        score = 0
        white_material = 0
        black_material = 0
        
        # Use piece_map() to iterate only over occupied squares
        piece_map = board.piece_map()
        
        # Track bishops for bonus
        white_bishops = 0
        black_bishops = 0
        
        for square, piece in piece_map.items():
            material = self.piece_values[piece.piece_type]
            
            # Position value with table
            table = None
            if piece.piece_type == chess.PAWN:
                table = self.pawn_table
            elif piece.piece_type == chess.KNIGHT:
                table = self.knight_table
            elif piece.piece_type == chess.BISHOP:
                table = self.bishop_table
            elif piece.piece_type == chess.ROOK:
                table = self.rook_table
            elif piece.piece_type == chess.QUEEN:
                table = self.queen_table
            elif piece.piece_type == chess.KING:
                # We'll handle king separately with blending
                pass
            
            pos_value = 0
            if table is not None:
                idx = square if piece.color == chess.WHITE else (7 - square//8)*8 + (square%8)
                pos_value = table[idx]
            
            if piece.color == chess.WHITE:
                score += material + pos_value
                white_material += material
                if piece.piece_type == chess.BISHOP:
                    white_bishops += 1
            else:
                score -= material + pos_value
                black_material += material
                if piece.piece_type == chess.BISHOP:
                    black_bishops += 1
        
        # Bishop pair bonus
        if white_bishops >= 2:
            score += 40
        if black_bishops >= 2:
            score -= 40
        
        # Pawn structure evaluation (cached)
        score += self.evaluate_pawn_structure(board)
        
        # Mobility – evaluate for both sides using null move (safer)
        current_moves = board.legal_moves.count()
        board.push(chess.Move.null())
        opponent_moves = board.legal_moves.count()
        board.pop()
        
        if board.turn == chess.WHITE:
            score += (current_moves - opponent_moves) * 5
        else:
            score -= (current_moves - opponent_moves) * 5
        
        # King safety: blend PST using endgame factor
        total_material = white_material + black_material
        endgame_factor = max(0.0, min(1.0, (4000 - total_material) / 2000))
        
        # Add king position value with blending
        for color, material_sum, sign in [(chess.WHITE, white_material, 1), (chess.BLACK, black_material, -1)]:
            king_sq = board.king(color)
            if king_sq is not None:
                idx = king_sq if color == chess.WHITE else (7 - king_sq//8)*8 + (king_sq%8)
                mid_val = self.king_middle_table[idx]
                end_val = self.king_end_table[idx]
                king_val = (1 - endgame_factor) * mid_val + endgame_factor * end_val
                score += sign * king_val
        
        # Return score from side to move perspective
        return score if board.turn == chess.WHITE else -score
    
    # --------------------------------------------------------------------------
    # Static Exchange Evaluation (SEE)
    # --------------------------------------------------------------------------
    def see(self, board: chess.Board, move: chess.Move) -> int:
        """
        Static Exchange Evaluation: estimate material gain of a capture.
        Positive means good for moving side.
        Simplified implementation for speed.
        """
        if not board.is_capture(move):
            return 0
        
        target = move.to_square
        from_sq = move.from_square
        piece = board.piece_at(from_sq)
        if not piece:
            return 0
        attacker_val = self.see_values[piece.piece_type]
        victim = board.piece_at(target)
        if not victim:
            return 0
        victim_val = self.see_values[victim.piece_type]
        
        # Very simple: if victim value > attacker value, it's good
        # In a full SEE we'd simulate sequence; but for move ordering this is often enough.
        return victim_val - attacker_val
    
    # --------------------------------------------------------------------------
    # Search with iterative deepening, transposition table, LMR, check extension, null move, aspiration windows
    # --------------------------------------------------------------------------
    def iterative_deepening_search(self, board: chess.Board, max_depth: int) -> Tuple[Optional[chess.Move], float]:
        """Perform iterative deepening search with time management and aspiration windows"""
        self.start_time = time.time()
        self.timeout = False
        self.nodes_searched = 0
        # Keep transposition table (do NOT clear)
        if len(self.tt) > self.tt_max_size:
            # Remove half of entries (crude but effective)
            keys = list(self.tt.keys())
            for k in keys[:len(keys)//2]:
                del self.tt[k]
        # Also clear pawn TT occasionally (optional)
        
        best_move = None
        best_value = -math.inf
        prev_eval = None  # for aspiration windows
        
        # Try depths from 2 to max_depth
        for depth in range(2, max_depth + 1):
            if self.timeout:
                break
                
            print(f"  Searching depth {depth}...")
            
            # Store PV move for move ordering at next depth
            self.pv_move = best_move
            
            # Aspiration windows: narrow window around previous score if we have one
            if prev_eval is not None and depth >= 4:
                alpha = prev_eval - self.aspiration_window
                beta  = prev_eval + self.aspiration_window
                # Search with narrow window
                for widen in range(self.aspiration_max_widening):
                    try:
                        current_best_move, current_best_value = self.alpha_beta_search(
                            board, depth, alpha, beta, 0, extended=False
                        )
                        # If inside window, done
                        if alpha < current_best_value < beta:
                            break
                        # Otherwise widen window and retry
                        alpha -= self.aspiration_window
                        beta  += self.aspiration_window
                    except Exception as e:
                        # Fallback to full window search
                        print(f"    Aspiration search error: {e}, using full window")
                        current_best_move, current_best_value = self.alpha_beta_search(
                            board, depth, -math.inf, math.inf, 0, extended=False
                        )
                        break
                else:
                    # If still outside after widening, do full window
                    current_best_move, current_best_value = self.alpha_beta_search(
                        board, depth, -math.inf, math.inf, 0, extended=False
                    )
            else:
                # First depth or shallow depth: full window
                current_best_move, current_best_value = self.alpha_beta_search(
                    board, depth, -math.inf, math.inf, 0, extended=False
                )
            
            if not self.timeout and current_best_move:
                best_move = current_best_move
                best_value = current_best_value
                prev_eval = best_value
                print(f"    Depth {depth}: eval = {best_value:.1f}, nodes = {self.nodes_searched}")
                
                # If we found a forced mate, no need to search deeper
                if abs(best_value) > 90000:
                    print(f"    Found forced mate, stopping search")
                    break
        
        print(f"  Search complete: {self.nodes_searched} nodes")
        return best_move, best_value
    
    def alpha_beta_search(self, board: chess.Board, depth: int, alpha: float, beta: float,
                         ply: int = 0, extended: bool = False) -> Tuple[Optional[chess.Move], float]:
        """
        Negamax alpha-beta search with TT, LMR, check extension, null move, futility pruning, reverse futility.
        extended: whether we already applied a check extension in this branch (to avoid over-extension)
        """
        # Check timeout every 1000 nodes
        if self.nodes_searched % 1000 == 0 and self.check_timeout():
            return None, 0
        
        self.nodes_searched += 1
        
        # Check extension (limit to once per branch and only when depth <= 2 to avoid explosion)
        if not extended and board.is_check() and depth <= 2 and depth < self.max_depth * 2:
            depth += 1
            extended = True
        
        # Transposition table lookup (public method if available)
        try:
            key = board.transposition_key()
        except AttributeError:
            key = board._transposition_key()  # fallback to private
        tt_entry = self.tt.get(key)
        if tt_entry and tt_entry['depth'] >= depth:
            if tt_entry['flag'] == 'exact':
                return tt_entry['move'], tt_entry['value']
            elif tt_entry['flag'] == 'lower':
                alpha = max(alpha, tt_entry['value'])
            elif tt_entry['flag'] == 'upper':
                beta = min(beta, tt_entry['value'])
            if alpha >= beta:
                return tt_entry['move'], tt_entry['value']
        
        # Terminal conditions
        if board.is_checkmate():
            return None, -100000 + ply
        if board.is_stalemate() or board.is_insufficient_material() or board.can_claim_threefold_repetition():
            return None, 0
        
        # Leaf node – quiescence search
        if depth == 0:
            return None, self.quiescence(board, alpha, beta, ply)
        
        # Material for pruning decisions
        total_material = sum(self.piece_values[p.piece_type] for p in board.piece_map().values())
        
        # Reverse futility pruning (at shallow depth)
        if depth <= 3 and not board.is_check() and not board.is_checkmate():
            static_eval = self.evaluate_position(board)
            margin = self.reverse_futility_margin_base * depth
            if static_eval - margin >= beta:
                return None, static_eval
        
        # Null-move pruning (if not in check, depth>=3, enough material, and not endgame)
        if (depth >= 3 and not board.is_check() and 
            total_material >= self.null_move_material_threshold and
            total_material > self.endgame_material_threshold):  # skip in endgames
            board.push(chess.Move.null())
            _, value = self.alpha_beta_search(board, depth - 1 - self.null_move_reduction, -beta, -beta+1, ply+1, extended)
            value = -value
            board.pop()
            if value >= beta:
                return None, beta
        
        # Generate and order moves
        moves = self.order_moves(board, ply)
        best_move = None
        best_value = -math.inf
        alpha_orig = alpha
        beta_orig = beta
        move_count = 0
        
        for move in moves:
            move_count += 1
            
            # Check timeout
            if self.timeout:
                break
            
            # Futility pruning at depth 1
            if depth == 1 and not board.is_check() and not board.is_capture(move) and not move.promotion:
                # Static evaluation of current position
                static_eval = self.evaluate_position(board)
                margin = self.futility_margin_base * depth
                # If even with margin we cannot raise alpha, skip (unless gives check)
                if static_eval + margin < alpha:
                    board.push(move)
                    gives_check = board.is_check()
                    board.pop()
                    if not gives_check:
                        continue
            
            # Late Move Reduction (LMR) - reduce depth for late quiet moves
            do_lmr = False
            reduction = 0
            if (move_count > 3 and depth >= 3 and 
                not board.is_capture(move) and not move.promotion and
                move not in self.killer_moves[ply]):
                # Reduction scales with move count and depth
                reduction = 1 + min(move_count // 6, depth // 2)
                reduction = min(reduction, depth - 1)  # cannot reduce below 0
                do_lmr = True
            
            board.push(move)
            
            if do_lmr:
                new_depth = depth - 1 - reduction
                if new_depth < 0:
                    new_depth = 0
                _, value = self.alpha_beta_search(board, new_depth, -beta, -alpha, ply + 1, extended)
                value = -value
                # If the reduced search causes a cutoff or is above alpha, re-search at full depth
                if value > alpha and value < beta and new_depth < depth - 1:
                    _, value = self.alpha_beta_search(board, depth - 1, -beta, -alpha, ply + 1, extended)
                    value = -value
            else:
                _, value = self.alpha_beta_search(board, depth - 1, -beta, -alpha, ply + 1, extended)
                value = -value
            
            board.pop()
            
            if value > best_value:
                best_value = value
                best_move = move
                alpha = max(alpha, value)
                if alpha >= beta:
                    # Store killer move and history
                    if not board.is_capture(move):
                        if move != self.killer_moves[ply][0]:
                            self.killer_moves[ply][1] = self.killer_moves[ply][0]
                            self.killer_moves[ply][0] = move
                        # Update history table with depth squared
                        self.history_table[move.from_square][move.to_square] += depth * depth
                    break
        
        # Store in transposition table
        if best_value <= alpha_orig:
            flag = 'upper'
        elif best_value >= beta_orig:
            flag = 'lower'
        else:
            flag = 'exact'
        self.tt[key] = {
            'depth': depth,
            'value': best_value,
            'flag': flag,
            'move': best_move
        }
        
        return best_move, best_value if best_value != -math.inf else 0
    
    def quiescence(self, board: chess.Board, alpha: float, beta: float, ply: int = 0) -> float:
        """Quiescence search – only captures, to avoid horizon effect."""
        stand_pat = self.evaluate_position(board)
        
        if stand_pat >= beta:
            return beta
        if stand_pat > alpha:
            alpha = stand_pat
        
        # Generate capture moves only
        capture_moves = [m for m in board.legal_moves if board.is_capture(m)]
        # Order captures by SEE
        capture_moves.sort(key=lambda m: self.see(board, m), reverse=True)
        
        for move in capture_moves:
            # Check timeout
            if self.check_timeout():
                break
            
            # Delta pruning – skip captures unlikely to raise alpha
            if self.delta_pruning(board, move, stand_pat, alpha, beta):
                continue
            
            board.push(move)
            score = -self.quiescence(board, -beta, -alpha, ply + 1)
            board.pop()
            
            if score >= beta:
                return beta
            if score > alpha:
                alpha = score
        
        return alpha
    
    def delta_pruning(self, board: chess.Board, move: chess.Move, stand_pat: float,
                     alpha: float, beta: float) -> bool:
        """Delta pruning – skip captures that cannot improve alpha."""
        if not board.is_capture(move):
            return False
            
        victim = board.piece_at(move.to_square)
        if not victim:
            return False
            
        victim_value = self.piece_values.get(victim.piece_type, 0)
        
        # If even after adding the victim's value we cannot reach alpha, prune
        if stand_pat + victim_value + 100 < alpha:
            return True
        
        return False
    
    def order_moves(self, board: chess.Board, ply: int = 0, is_qsearch: bool = False) -> List[chess.Move]:
        """Order moves for better alpha-beta pruning"""
        moves = list(board.legal_moves)
        
        # If very few moves, don't spend time sorting
        if len(moves) <= 3:
            return moves
        
        move_scores = []
        
        for move in moves:
            score = 0
            
            # 0. PV move from previous iteration (highest priority)
            if self.pv_move == move:
                score = 20000
            
            # 1. Captures (ordered by SEE)
            if board.is_capture(move):
                score += 10000 + self.see(board, move)
            
            # 2. Promotions
            elif move.promotion:
                score += 9000 + self.piece_values.get(move.promotion, 0)
            
            # 3. Killer moves (only in main search)
            elif not is_qsearch:
                if self.killer_moves[ply][0] == move:
                    score += 8000
                elif self.killer_moves[ply][1] == move:
                    score += 7000
            
            # 4. History heuristic (scaled down to not dominate)
            if not board.is_capture(move) and not move.promotion:
                score += self.history_table[move.from_square][move.to_square] // 10
            
            # 5. Simple positional bonuses
            piece = board.piece_at(move.from_square)
            if piece:
                # Center control
                to_file = chess.square_file(move.to_square)
                to_rank = chess.square_rank(move.to_square)
                
                # Bonus for moving to center
                if 2 <= to_file <= 5 and 2 <= to_rank <= 5:
                    score += 50
                
                # Bonus for developing pieces early
                if board.fullmove_number < 10:
                    if piece.piece_type in [chess.KNIGHT, chess.BISHOP]:
                        if move.from_square in [chess.B1, chess.G1, chess.B8, chess.G8,
                                               chess.C1, chess.F1, chess.C8, chess.F8]:
                            score += 100
                
                # Bonus for castling
                if board.is_castling(move):
                    score += 300
            
            move_scores.append((move, score))
        
        # Sort by score (highest first)
        move_scores.sort(key=lambda x: x[1], reverse=True)
        return [move for move, _ in move_scores]
    
    def get_best_move(self, fen: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """Get the best move for given position with time management"""
        try:
            board = chess.Board(fen)
            
            if board.is_game_over():
                return None, None, None
            
            print(f"🤖 Engine thinking (difficulty: {self.difficulty}, time limit: {self.max_time}s)...")
            
            # Determine search depth based on position complexity
            legal_moves = list(board.legal_moves)
            
            # Adjust depth based on position complexity
            if len(legal_moves) > 40:  # Very complex position
                effective_depth = min(self.target_depth - 1, 4)
            elif len(legal_moves) > 25:  # Complex position
                effective_depth = min(self.target_depth, 5)
            else:  # Normal position
                effective_depth = self.target_depth
            
            print(f"  Position has {len(legal_moves)} legal moves, searching to depth {effective_depth}")
            
            # Perform iterative deepening search
            best_move, eval_score = self.iterative_deepening_search(board, effective_depth)
            
            # If search timed out or found no move, use fallback
            if not best_move or self.timeout:
                print(f"  {'Timeout' if self.timeout else 'No move found'}, using best available move")
                
                # Try to use the last best move found
                if not best_move:
                    # Order moves and pick the best one based on simple evaluation
                    ordered_moves = self.order_moves(board)
                    
                    # Evaluate first few moves quickly
                    best_score = -math.inf
                    for move in ordered_moves[:5]:  # Only check first 5
                        board.push(move)
                        score = self.evaluate_position(board)
                        board.pop()
                        
                        if score > best_score:
                            best_score = score
                            best_move = move
            
            # Final fallback: random move
            if not best_move:
                print("  Using random move as fallback")
                best_move = random.choice(list(board.legal_moves))
            
            # Convert move to string format
            from_sq = chess.square_name(best_move.from_square)
            to_sq = chess.square_name(best_move.to_square)
            promotion = chess.piece_symbol(best_move.promotion).lower() if best_move.promotion else None
            
            elapsed = time.time() - self.start_time if self.start_time else 0
            print(f"✅ Engine move: {from_sq} -> {to_sq} (eval: {eval_score:.1f}, time: {elapsed:.1f}s)")
            
            return from_sq, to_sq, promotion
            
        except Exception as e:
            print(f"❌ Engine error: {e}")
            import traceback
            traceback.print_exc()
            
            # Last resort: random move
            try:
                board = chess.Board(fen)
                if board.is_game_over():
                    return None, None, None
                
                move = random.choice(list(board.legal_moves))
                from_sq = chess.square_name(move.from_square)
                to_sq = chess.square_name(move.to_square)
                promotion = chess.piece_symbol(move.promotion).lower() if move.promotion else None
                
                return from_sq, to_sq, promotion
            except:
                return None, None, None


# Test the engine
if __name__ == "__main__":
    print("🧪 Testing Optimized Chess Engine...")
    
    # Test each difficulty level
    for difficulty in range(1, 5):
        print(f"\n{'='*50}")
        print(f"Testing difficulty {difficulty}")
        print('='*50)
        
        engine = StrongChessEngine(difficulty=difficulty)
        
        # Test with starting position
        test_fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        
        start_time = time.time()
        result = engine.get_best_move(test_fen)
        elapsed = time.time() - start_time
        
        if result[0]:
            print(f"✅ Difficulty {difficulty}: {result[0]} -> {result[1]} (time: {elapsed:.1f}s)")
            if elapsed > engine.max_time * 1.1:  # 10% tolerance
                print(f"⚠️  Warning: Slightly over time limit ({elapsed:.1f}s > {engine.max_time}s)")
        else:
            print(f"❌ Difficulty {difficulty} test failed")