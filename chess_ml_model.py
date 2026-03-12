"""
Chess ML Model Integration - Neural Network Version (Fully Optimized)
Trained on 16.5M positions with PyTorch (4.9M parameters)
- Fixed evaluation scaling for consistent centipawn values
- Automatic device detection (CPU/GPU)
- Half-precision inference for speed
- Evaluation statistics tracking
- Robust error handling
- LRU caching for repeated positions
"""

import chess
import time
import os
import sys
import numpy as np
from functools import lru_cache
from typing import Optional, List, Tuple
import json

try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    print("⚠️  PyTorch not installed – ML model will not work.")
    # Dummy classes to allow module loading
    class nn:
        class Module:
            pass
    torch = None

# ------------------------------------------------------------
# Device detection with CUDA fallback
# ------------------------------------------------------------
def get_optimal_device():
    """Returns the best available device with CUDA if available."""
    if not TORCH_AVAILABLE:
        return torch.device('cpu')
    if torch.cuda.is_available():
        device = torch.device('cuda')
        # Optimize CUDA performance
        torch.backends.cudnn.benchmark = True
        torch.backends.cudnn.deterministic = False
        return device
    # CPU optimizations
    if hasattr(torch, 'set_num_threads'):
        torch.set_num_threads(os.cpu_count() or 4)
    return torch.device('cpu')


# ------------------------------------------------------------
# Exact definition of the ChessNN class used during training
# ------------------------------------------------------------
class ChessNN(nn.Module):
    """CNN for chess position evaluation (same as in training script)."""
    
    def __init__(self):
        super().__init__()
        
        # Initial convolution
        self.conv1 = nn.Conv2d(20, 128, kernel_size=3, padding=1)
        self.bn1 = nn.BatchNorm2d(128)
        
        # Residual blocks
        self.res_block1 = self._make_res_block(128, 128)
        self.res_block2 = self._make_res_block(128, 256, stride=2)
        self.res_block3 = self._make_res_block(256, 512, stride=2)
        
        # Global pooling
        self.global_pool = nn.AdaptiveAvgPool2d(1)
        
        # Value head
        self.value_head = nn.Sequential(
            nn.Linear(512, 256),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(128, 1),
            nn.Tanh()
        )
        
        self._init_weights()
    
    def _make_res_block(self, in_channels, out_channels, stride=1):
        return nn.Sequential(
            nn.Conv2d(in_channels, out_channels, kernel_size=3, stride=stride, padding=1),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(),
            nn.Conv2d(out_channels, out_channels, kernel_size=3, padding=1),
            nn.BatchNorm2d(out_channels)
        )
    
    def _init_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='relu')
            elif isinstance(m, nn.BatchNorm2d):
                nn.init.constant_(m.weight, 1)
                nn.init.constant_(m.bias, 0)
            elif isinstance(m, nn.Linear):
                nn.init.normal_(m.weight, 0, 0.01)
                nn.init.constant_(m.bias, 0)
    
    def forward(self, x):
        # Initial conv
        x = torch.relu(self.bn1(self.conv1(x)))
        identity = x
        x = self.res_block1(x)
        x = torch.relu(x + identity)
        x = self.res_block2(x)
        x = self.res_block3(x)
        x = self.global_pool(x)
        x = x.view(x.size(0), -1)
        value = self.value_head(x)
        return value


# ------------------------------------------------------------
# Optimized FEN to tensor conversion
# ------------------------------------------------------------
_PIECE_MAP = {
    chess.PAWN: 0, chess.KNIGHT: 1, chess.BISHOP: 2,
    chess.ROOK: 3, chess.QUEEN: 4, chess.KING: 5
}

@lru_cache(maxsize=1024)
def fen_to_tensor_helper(fen: str) -> torch.Tensor:
    """
    Convert FEN to 20x8x8 tensor for evaluation.
    Cached for repeated positions to avoid recomputation.
    """
    try:
        board = chess.Board(fen)
        tensor = np.zeros((20, 8, 8), dtype=np.float32)

        # Piece channels (12)
        for square in chess.SQUARES:
            piece = board.piece_at(square)
            if piece:
                row, col = divmod(square, 8)
                color_offset = 0 if piece.color == chess.WHITE else 6
                piece_idx = _PIECE_MAP[piece.piece_type]
                channel = color_offset + piece_idx
                tensor[channel, row, col] = 1.0

        # Side to move (channel 12)
        tensor[12, :, :] = 1.0 if board.turn == chess.WHITE else 0.0

        # Castling rights (channels 13-16)
        tensor[13, :, :] = 1.0 if board.has_kingside_castling_rights(chess.WHITE) else 0.0
        tensor[14, :, :] = 1.0 if board.has_queenside_castling_rights(chess.WHITE) else 0.0
        tensor[15, :, :] = 1.0 if board.has_kingside_castling_rights(chess.BLACK) else 0.0
        tensor[16, :, :] = 1.0 if board.has_queenside_castling_rights(chess.BLACK) else 0.0

        # En passant (channel 17)
        tensor[17, :, :] = 1.0 if board.ep_square is not None else 0.0

        # Move counters (channels 18-19) - normalized to [0,1]
        tensor[18, :, :] = min(board.halfmove_clock / 100.0, 1.0)
        tensor[19, :, :] = min(board.fullmove_number / 100.0, 1.0)

        return torch.from_numpy(tensor)
    except Exception as e:
        print(f"Error converting FEN: {e}")
        return torch.zeros(20, 8, 8)


# ------------------------------------------------------------
# WrappedModel class – optimized evaluate() with consistent scaling
# ------------------------------------------------------------
class WrappedModel:
    """Wrapper that provides fast, consistent evaluation."""
    
    # Evaluation constants for consistent scaling
    CENTIPAWN_SCALE = 300.0
    MATE_SCORE = 100000
    MAX_CENTIPAWN = 10000
    
    def __init__(self, model: nn.Module, device: torch.device, use_half: bool = True):
        self.model = model
        self.device = device
        self.use_half = use_half and (device.type == 'cuda')
        
        # Convert model to half if using GPU
        if self.use_half:
            self.model = self.model.half()
        
        self.model.eval()
        
        # Optional: compile model for faster inference (PyTorch 2.0+)
        if hasattr(torch, 'compile') and device.type == 'cuda':
            try:
                self.model = torch.compile(self.model, mode='reduce-overhead')
                print("   Model compiled with torch.compile")
            except Exception:
                pass
        
        # Evaluation statistics for normalization (optional)
        self.eval_stats = {
            'mean': 0.0,
            'std': 300.0,
            'min': -10000,
            'max': 10000,
            'samples': []
        }
        self.collect_stats = True
        self.max_stats_samples = 1000
        
    def _normalize_centipawns(self, raw_value: float) -> float:
        """
        Convert raw network output (-1 to 1) to consistent centipawns.
        Uses arctanh scaling with bounds to prevent extreme values.
        """
        # Clip to safe range for arctanh
        clipped = max(-0.99, min(0.99, raw_value))
        
        # Convert to centipawns using inverse tanh
        centipawns = self.CENTIPAWN_SCALE * np.arctanh(clipped)
        
        # Bound to reasonable range
        centipawns = max(-self.MAX_CENTIPAWN, min(self.MAX_CENTIPAWN, centipawns))
        
        return centipawns
    
    @torch.no_grad()
    def evaluate(self, fen: str) -> float:
        """Evaluate a single position, returning centipawn score."""
        try:
            # Handle terminal positions quickly
            board = chess.Board(fen)
            if board.is_checkmate():
                return -self.MATE_SCORE if board.turn == chess.WHITE else self.MATE_SCORE
            if board.is_stalemate() or board.is_insufficient_material():
                return 0.0
            
            # Convert FEN to tensor
            tensor = fen_to_tensor_helper(fen).to(self.device)
            
            # Add batch dimension and optionally convert to half
            if self.use_half:
                tensor = tensor.half()
            tensor = tensor.unsqueeze(0)
            
            # Run inference
            normalized = self.model(tensor).item()
            
            # Convert to centipawns
            centipawns = self._normalize_centipawns(normalized)
            
            # Collect statistics (optional)
            if self.collect_stats and len(self.eval_stats['samples']) < self.max_stats_samples:
                self.eval_stats['samples'].append(centipawns)
                if len(self.eval_stats['samples']) == self.max_stats_samples:
                    self.eval_stats['mean'] = float(np.mean(self.eval_stats['samples']))
                    self.eval_stats['std'] = float(np.std(self.eval_stats['samples']))
                    self.eval_stats['min'] = float(np.min(self.eval_stats['samples']))
                    self.eval_stats['max'] = float(np.max(self.eval_stats['samples']))
                    print(f"📊 Evaluation stats: mean={self.eval_stats['mean']:.1f}, "
                          f"std={self.eval_stats['std']:.1f}, "
                          f"range=[{self.eval_stats['min']:.0f}, {self.eval_stats['max']:.0f}]")
                    self.collect_stats = False
            
            return centipawns
            
        except Exception as e:
            print(f"Evaluation error: {e}")
            return 0.0
    
    @torch.no_grad()
    def evaluate_batch(self, fens: List[str]) -> List[float]:
        """
        Evaluate multiple positions in a batch for higher throughput.
        Useful for move generation during search.
        """
        if not fens:
            return []
        
        try:
            # Convert all FENs to tensors
            tensors = []
            for fen in fens:
                tensors.append(fen_to_tensor_helper(fen))
            
            # Stack into batch
            batch = torch.stack(tensors).to(self.device)
            if self.use_half:
                batch = batch.half()
            
            # Run inference
            normalized = self.model(batch).cpu().numpy().flatten()
            
            # Convert each to centipawns
            results = []
            for val in normalized:
                results.append(self._normalize_centipawns(float(val)))
            
            return results
            
        except Exception as e:
            print(f"Batch evaluation error: {e}")
            return [0.0] * len(fens)


# ------------------------------------------------------------
# Make classes available in __main__ for pickle compatibility
# ------------------------------------------------------------
sys.modules['__main__'].ChessNN = ChessNN
sys.modules['__main__'].WrappedModel = WrappedModel
sys.modules['__main__'].fen_to_tensor_helper = fen_to_tensor_helper


# ------------------------------------------------------------
# Main ChessMLModel class – optimized with caching
# ------------------------------------------------------------
class ChessMLModel:
    """Neural chess evaluator trained on 16.5M positions (fully optimized)."""

    def __init__(self, model_path: Optional[str] = None, use_half: bool = True):
        self.model = None
        self.load_time = None
        self.device = get_optimal_device()
        self.use_half = use_half and (self.device.type == 'cuda')
        
        # Evaluation cache using LRU
        self.evaluate_position = lru_cache(maxsize=20000)(self._evaluate_position_impl)
        
        # Track statistics
        self.stats = {
            'total_evaluations': 0,
            'cache_hits': 0,
            'avg_time_ms': 0
        }

        if not TORCH_AVAILABLE:
            print("⚠️  PyTorch not installed – cannot load ML model.")
            return

        try:
            start_time = time.time()
            print(f"🔄 Loading ML model (device: {self.device}, half: {self.use_half})...")

            # Locate model file
            if model_path is None:
                base_dir = os.path.dirname(os.path.abspath(__file__))
                candidates = [
                    os.path.join(base_dir, "models", "chess_nn_full.pth"),
                    os.path.join(base_dir, "models", "chess_evaluator.pth"),
                    os.path.join(base_dir, "chess_nn_full.pth"),
                    os.path.join(base_dir, "chess_evaluator.pth"),
                    "models/chess_nn_full.pth",
                    "models/chess_evaluator.pth",
                    "chess_nn_full.pth",
                    "chess_evaluator.pth"
                ]
                for path in candidates:
                    if os.path.exists(path):
                        model_path = path
                        break

            if not model_path or not os.path.exists(model_path):
                print(f"❌ No model file found. Searched in:")
                for path in candidates[:6]:
                    print(f"   - {path}")
                return

            print(f"📂 Found model at: {model_path}")

            # Load the saved data (always map to CPU first)
            saved_data = torch.load(model_path, map_location='cpu', weights_only=False)

            # Extract state_dict (handles various save formats)
            state_dict = self._extract_state_dict(saved_data)
            if state_dict is None:
                raise ValueError("Could not locate state_dict in saved file")

            # Instantiate model and load weights
            model = ChessNN()
            
            # Clean state_dict keys if needed (remove 'module.' prefix from DataParallel)
            state_dict = {k.replace('module.', ''): v for k, v in state_dict.items()}
            
            model.load_state_dict(state_dict)
            model.eval()

            # Move model to target device
            model = model.to(self.device)
            
            # Wrap the model with optimized evaluator
            self.model = WrappedModel(model, self.device, use_half=self.use_half)

            self.load_time = time.time() - start_time
            print(f"✅ ML Model loaded successfully in {self.load_time:.2f}s")
            print(f"   Device: {self.device}, Model type: {type(self.model).__name__}")

            # Test evaluation to verify
            test_fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
            test_eval = self.evaluate_position(test_fen)
            print(f"   Test eval (starting position): {test_eval:.1f} cp")
            
            # Test a few more positions to warm up
            test_positions = [
                "r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 0 1",  # Sicilian
                "8/8/8/8/8/1k6/8/K7 w - - 0 1",  # King vs King
                "8/8/8/8/8/1k6/1Q6/K7 w - - 0 1",  # KQ vs K
            ]
            print("   Test evaluations:")
            for fen in test_positions:
                eval_score = self.evaluate_position(fen)
                print(f"     {fen[:40]}...: {eval_score:.1f} cp")

        except Exception as e:
            print(f"❌ ML model loading failed: {e}")
            import traceback
            traceback.print_exc()
            self.model = None

    def _extract_state_dict(self, saved_data):
        """Extract state_dict from various save formats."""
        if isinstance(saved_data, dict):
            # Check common keys
            if "model_state_dict" in saved_data:
                return saved_data["model_state_dict"]
            elif "state_dict" in saved_data:
                return saved_data["state_dict"]
            elif any('weight' in k for k in saved_data.keys()):
                return saved_data
            else:
                # Search for any nested dict that looks like state_dict
                for key, value in saved_data.items():
                    if isinstance(value, dict) and any('weight' in str(k) for k in value.keys()):
                        print(f"   Found state_dict in key: '{key}'")
                        return value
        elif hasattr(saved_data, 'state_dict'):
            return saved_data.state_dict()
        return None

    def _evaluate_position_impl(self, fen: str) -> float:
        """Internal evaluation without caching (called by LRU wrapper)."""
        if self.model is None:
            return 0.0

        start_time = time.time()
        
        try:
            score = self.model.evaluate(fen)
            
            # Update statistics
            self.stats['total_evaluations'] += 1
            elapsed = (time.time() - start_time) * 1000  # ms
            self.stats['avg_time_ms'] = 0.9 * self.stats['avg_time_ms'] + 0.1 * elapsed
            
            return score
            
        except Exception as e:
            print(f"ML evaluation error: {e}")
            return 0.0

    def evaluate_position(self, fen: str) -> float:
        """Public evaluation method with caching."""
        if fen in self.__dict__.get('_cache', {}):
            self.stats['cache_hits'] += 1
        return self._evaluate_position_impl(fen)

    def evaluate_batch(self, fens: List[str]) -> List[float]:
        """Evaluate multiple positions in batch mode."""
        if self.model is None:
            return [0.0] * len(fens)
        return self.model.evaluate_batch(fens)

    def get_stats(self) -> dict:
        """Return evaluation statistics."""
        stats = self.stats.copy()
        if hasattr(self.evaluate_position, 'cache_info'):
            stats['cache'] = {
                'hits': self.evaluate_position.cache_info().hits,
                'misses': self.evaluate_position.cache_info().misses,
                'size': self.evaluate_position.cache_info().currsize,
                'maxsize': self.evaluate_position.cache_info().maxsize,
            }
        return stats

    def is_loaded(self) -> bool:
        return self.model is not None

    def clear_cache(self):
        """Clear the evaluation cache."""
        self.evaluate_position.cache_clear()
        fen_to_tensor_helper.cache_clear()
        print("🧹 Cache cleared")

    def get_info(self) -> dict:
        """Return model information for API."""
        return {
            'loaded': self.is_loaded(),
            'load_time': self.load_time,
            'device': str(self.device),
            'half_precision': self.use_half,
            'model_type': 'Residual CNN (4.9M params)',
            'training_data': '16.5M positions',
            'stats': self.get_stats()
        }