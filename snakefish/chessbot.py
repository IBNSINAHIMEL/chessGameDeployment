class FallbackEngine:
    """Simple fallback engine if snakefish is not available"""
    
    def __init__(self, difficulty=2):
        self.difficulty = difficulty
        self.search_depth = difficulty + 1  # 3-5 ply
    
    def get_best_move(self, fen):
        """Simple random move fallback"""
        import random
        
        # Parse FEN to get board position
        # This is a simplified version - you should use python-chess for this
        board = self.fen_to_simple_board(fen)
        
        # Get all pieces for current player
        current_player = 'w' if 'w' in fen.split()[1] else 'b'
        pieces = []
        
        for square, piece in board.items():
            if piece.startswith(current_player):
                pieces.append(square)
        
        if not pieces:
            return None, None, None
        
        # Pick a random piece and move
        import random
        from_square = random.choice(pieces)
        
        # Generate random moves (simplified)
        moves = self.generate_random_moves(from_square, board, current_player)
        
        if not moves:
            return None, None, None
        
        to_square = random.choice(moves)
        
        return from_square, to_square, None
    
    def fen_to_simple_board(self, fen):
        """Convert FEN to simple board dictionary"""
        board = {}
        fen_parts = fen.split()
        board_fen = fen_parts[0]
        
        ranks = board_fen.split('/')
        
        for rank_idx, rank in enumerate(ranks):
            rank_num = 8 - rank_idx
            file_idx = 0
            
            for char in rank:
                if char.isdigit():
                    file_idx += int(char)
                else:
                    square = chr(ord('a') + file_idx) + str(rank_num)
                    board[square] = char
                    file_idx += 1
        
        return board
    
    def generate_random_moves(self, from_square, board, player):
        """Generate random legal moves (simplified)"""
        # This is a very simplified move generator
        # For a proper implementation, use python-chess
        moves = []
        
        file = from_square[0]
        rank = int(from_square[1])
        
        # Generate some basic moves
        if player == 'w':
            # White pawn moves
            if board.get(from_square, '').lower() == 'p':
                # Move forward
                if rank < 8:
                    moves.append(file + str(rank + 1))
        else:
            # Black pawn moves
            if board.get(from_square, '').lower() == 'p':
                # Move forward
                if rank > 1:
                    moves.append(file + str(rank - 1))
        
        return moves