$(document).ready(function() {
    console.log('Chess Game Initializing...');
    
    // Game state variables
    let gameState = {
        board: null,
        selectedSquare: null,
        validMoves: [],
        moveHistory: [],
        fenHistory: [], // Store FEN states for undo
        currentFen: 'start',
        gameMode: 'two-player',
        playerSide: 'white',
        difficulty: 3,
        isWhiteTurn: true,
        isGameOver: false,
        boardFlipped: false,
        mlMode: 'fast'  // 'fast' or 'deep'
    };

    // ==================== SOUND MANAGER ====================
    const SoundManager = {
        sounds: {},
        enabled: true,
        
        init() {
            // Initialize all sound objects with your files
            this.sounds = {
                move: new Audio('/static/sounds/move.mp3'),           // All regular moves
                horse_move: new Audio('/static/sounds/horse_move.mp3'), // Knight moves only
                capture: new Audio('/static/sounds/capture.mp3'),     // Captures
                check: new Audio('/static/sounds/check.mp3'),         // Check
                gameover: new Audio('/static/sounds/gameover.mp3'),   // Game over
                warning: new Audio('/static/sounds/warning.mp3'),     // Warnings
                castle: new Audio('/static/sounds/castle.mp3')        // Castling
            };
            
            // Preload and configure sounds
            Object.values(this.sounds).forEach(sound => {
                sound.load();
                sound.volume = 0.7; // Default volume
            });
            
            // Check if audio is supported
            if (!window.Audio) {
                console.warn('Audio not supported');
                this.enabled = false;
            }
            
            // Load saved preference
            const savedSound = localStorage.getItem('sound-enabled');
            if (savedSound === 'false') {
                this.enabled = false;
            }
            
            console.log('✅ Sound Manager initialized with all sounds');
            console.log('   📢 move.mp3 - All regular moves (user & bot)');
            console.log('   🐴 horse_move.mp3 - Knight moves only');
            console.log('   👑 castle.mp3 - Castling');
            console.log('   ⚔️ capture.mp3 - Captures');
            console.log('   ⚠️ check.mp3 - Check');
            console.log('   🎮 gameover.mp3 - Game over');
            console.log('   ⚠️ warning.mp3 - Warnings');
        },
        
        play(soundName) {
            if (!this.enabled) return;
            
            const sound = this.sounds[soundName];
            if (sound) {
                // Clone to allow overlapping playback
                const soundClone = sound.cloneNode();
                soundClone.volume = sound.volume;
                soundClone.play().catch(e => {
                    // Autoplay might be blocked - user needs to interact first
                    console.log('Sound play failed (user interaction needed):', e);
                });
            }
        },
        
        toggle() {
            this.enabled = !this.enabled;
            localStorage.setItem('sound-enabled', this.enabled);
            return this.enabled;
        },
        
        setVolume(level) {
            Object.values(this.sounds).forEach(sound => {
                sound.volume = Math.max(0, Math.min(1, level));
            });
            localStorage.setItem('sound-volume', level);
        }
    };

    // Initialize sound manager
    SoundManager.init();

    // Mobile optimization functions
    function setupMobileOptimizations() {
        const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
        
        if (isMobile) {
            console.log('Mobile device detected, optimizing for touch...');
            document.body.classList.add('mobile-device');
            
            document.addEventListener('touchstart', function(e) {
                if (e.touches.length > 1) e.preventDefault();
            }, { passive: false });
            
            document.addEventListener('contextmenu', function(e) {
                e.preventDefault();
                return false;
            });
            
            window.addEventListener('orientationchange', function() {
                setTimeout(() => {
                    if (gameState.board) gameState.board.resize();
                }, 100);
            });
        }
    }

    function optimizeBoardForMobile() {
        if (!/Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent)) return;
        
        const vw = window.innerWidth * 0.01;
        const isPortrait = window.innerHeight > window.innerWidth;
        
        if (isPortrait) {
            $('.chessboard-container').css('max-width', Math.min(vw * 85, 600) + 'px');
        } else {
            $('.chessboard-container').css('max-width', Math.min(vw * 70, 500) + 'px');
        }
        
        if (gameState.board && typeof gameState.board.resize === 'function') {
            setTimeout(() => gameState.board.resize(), 50);
        }
    }

    // Initialize the chessboard
    function initBoard() {
        console.log('Initializing chessboard...');
        
        const boardConfig = {
            draggable: true,
            dropOffBoard: 'snapback',
            position: 'start',
            onDragStart: onDragStart,
            onDrop: onDrop,
            onSnapEnd: onSnapEnd,
            pieceTheme: '/static/img/chesspieces/wikipedia/{piece}.png',
            orientation: 'white',
            appearSpeed: 200,
            moveSpeed: 200,
            snapbackSpeed: 100,
            snapSpeed: 50
        };
        
        gameState.board = Chessboard('board', boardConfig);
        
        if (gameState.board) {
            console.log('✅ Chessboard initialized successfully');
            setupBoardEvents();
        } else {
            console.error('❌ Chessboard failed to initialize');
        }
    }

    // Setup custom board events for click-to-move
    function setupBoardEvents() {
        const $board = $('#board .board-b72b1');
        
        $board.off('click').on('click', '.square-55d63', function(e) {
            e.preventDefault();
            e.stopPropagation();
            handleSquareClick($(this).data('square'));
        });
        
        $board.off('touchstart').on('touchstart', '.square-55d63', function(e) {
            e.preventDefault();
            e.stopPropagation();
            handleSquareClick($(this).data('square'));
        });
        
        $board.off('mousedown touchstart', '.piece-417db').on('mousedown touchstart', '.piece-417db', function(e) {
            e.stopPropagation();
        });
    }

    // Handle square click/touch
    function handleSquareClick(square) {
        if (gameState.isGameOver) {
            SoundManager.play('warning');
            showMessage('Game is over! Start a new game.');
            return;
        }
        
        // In vs bot or vs ml mode, check if it's player's turn
        if (gameState.gameMode === 'vs-bot' || gameState.gameMode === 'vs-ml') {
            const playerColor = gameState.playerSide.charAt(0);
            const currentTurnColor = gameState.isWhiteTurn ? 'w' : 'b';
            
            if (playerColor !== currentTurnColor) {
                SoundManager.play('warning');
                showMessage("It's the AI's turn!");
                return;
            }
        }
        
        const position = gameState.board.position();
        const piece = position[square];
        
        if (gameState.selectedSquare) {
            if (square === gameState.selectedSquare) {
                clearSelection();
                return;
            }
            
            const isValidMove = gameState.validMoves.some(move => move.to === square);
            
            if (isValidMove) {
                makeMove(gameState.selectedSquare, square).then(success => {
                    if (!success) clearSelection();
                });
                return;
            }
            
            if (piece) {
                const pieceColor = piece.charAt(0);
                const currentTurnColor = gameState.isWhiteTurn ? 'w' : 'b';
                
                if (pieceColor === currentTurnColor) {
                    selectPiece(square);
                    return;
                }
            }
            
            clearSelection();
            return;
        }
        
        if (piece) {
            const pieceColor = piece.charAt(0);
            const currentTurnColor = gameState.isWhiteTurn ? 'w' : 'b';
            
            if (pieceColor === currentTurnColor) {
                selectPiece(square);
            } else {
                SoundManager.play('warning');
                showMessage("It's not your turn!");
            }
        }
    }

    // Select a piece and show its valid moves
    async function selectPiece(square) {
        clearSelection();
        
        gameState.selectedSquare = square;
        $(`[data-square="${square}"]`).addClass('selected');
        
        // Optional: soft click sound when selecting piece (uncomment if desired)
        // SoundManager.play('move');
        
        try {
            const moves = await getLegalMoves(square);
            gameState.validMoves = moves;
            
            moves.forEach(move => {
                const $targetSquare = $(`[data-square="${move.to}"]`);
                const position = gameState.board.position();
                
                if (position[move.to]) {
                    $targetSquare.addClass('valid-capture');
                } else {
                    $targetSquare.addClass('valid-move');
                }
            });
        } catch (error) {
            console.error('Error getting legal moves:', error);
            clearSelection();
        }
    }

    // Clear selection and highlights
    function clearSelection() {
        gameState.selectedSquare = null;
        gameState.validMoves = [];
        $('.square-55d63').removeClass('selected valid-move valid-capture');
    }

    // Get legal moves from server
    async function getLegalMoves(square) {
        try {
            const response = await fetch('/get_legal_moves', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    fen: getCurrentFEN(),
                    square: square
                })
            });
            
            const data = await response.json();
            if (data.error) throw new Error(data.error);
            
            return data.legal_moves.map(move => ({
                from: square,
                to: move,
                promotion: null
            }));
        } catch (error) {
            console.error('Error fetching legal moves:', error);
            return [];
        }
    }

    // Make a move
    async function makeMove(from, to, promotion = null) {
        console.log('Making move:', from, '->', to, 'promotion:', promotion);
        
        try {
            const response = await fetch('/validate_move', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    fen: getCurrentFEN(),
                    from: from,
                    to: to,
                    promotion: promotion
                })
            });
            
            const data = await response.json();
            
            if (!data.valid) {
                if (data.requires_promotion) {
                    const position = gameState.board.position();
                    const piece = position[from];
                    const color = piece ? piece.charAt(0) : (gameState.isWhiteTurn ? 'w' : 'b');
                    
                    try {
                        const promotionPiece = await getPromotionPiece(color, from, to);
                        if (!promotionPiece) {
                            showMessage('Promotion cancelled');
                            return false;
                        }
                        return await makeMove(from, to, promotionPiece);
                    } catch (error) {
                        console.error('Error getting promotion piece:', error);
                        SoundManager.play('warning');
                        showMessage('Promotion error');
                        return false;
                    }
                }
                SoundManager.play('warning');
                showMessage(data.error || 'Invalid move');
                return false;
            }
            
            // Get the piece that moved
            const position = gameState.board.position();
            const piece = position[from];
            const pieceType = piece ? piece.charAt(1) : '';
            const wasCapture = position[to] !== undefined;
            const isCastle = piece && piece.charAt(1) === 'k' && Math.abs(to.charCodeAt(0) - from.charCodeAt(0)) === 2;
            
            // 🎵 DETERMINE WHICH SOUND TO PLAY 🎵
            if (isCastle) {
                // Castling sound
                SoundManager.play('castle');
            } 
            else if (pieceType === 'N') {
                // Knight move - play horse sound
                SoundManager.play('horse_move');
            }
            else if (wasCapture) {
                // Capture sound
                SoundManager.play('capture');
            }
            else {
                // Regular move sound for ALL other moves (user AND bot)
                SoundManager.play('move');
            }
            
            // Save current FEN for undo
            gameState.fenHistory.push(getCurrentFEN());
            
            // Update game state
            gameState.currentFen = data.fen;
            gameState.isWhiteTurn = !gameState.isWhiteTurn;
            gameState.isGameOver = data.checkmate || data.stalemate || data.draw;
            
            // Update board
            gameState.board.position(data.fen);
            clearSelection();
            updateGameStatus(data);
            
            // Add to move history
            const moveNotation = getMoveNotation(from, to, promotion);
            gameState.moveHistory.push({
                move: moveNotation,
                color: gameState.isWhiteTurn ? 'black' : 'white'
            });
            updateMoveHistory();
            updateControlButtons();
            
            // Play check sound if needed
            if (data.check) {
                setTimeout(() => SoundManager.play('check'), 200);
            }
            
            if (gameState.isGameOver) {
                SoundManager.play('gameover');
                showGameOverMessage(data);
            } else {
                // If vs bot/ml and it's AI's turn, get AI move
                if ((gameState.gameMode === 'vs-bot' || gameState.gameMode === 'vs-ml') && 
                    ((gameState.playerSide === 'white' && !gameState.isWhiteTurn) ||
                     (gameState.playerSide === 'black' && gameState.isWhiteTurn))) {
                    
                    gameState.fenHistory.push(getCurrentFEN());
                    setTimeout(getBotOrMLMove, 500);
                }
            }
            
            return true;
        } catch (error) {
            console.error('Error making move:', error);
            SoundManager.play('warning');
            showMessage('Error making move: ' + error.message);
            return false;
        }
    }

    // Get promotion piece from user
    async function getPromotionPiece(color, from, to) {
        if (!window.showPromotionModal) {
            console.error('showPromotionModal not available, defaulting to queen');
            return 'q';
        }
        
        try {
            return await window.showPromotionModal(color, from, to);
        } catch (error) {
            console.error('Error in showPromotionModal:', error);
            return 'q';
        }
    }

    // Unified function to get bot/ML move
    async function getBotOrMLMove() {
        if (gameState.isGameOver) return;
        
        const isMLMode = gameState.gameMode === 'vs-ml';
        showMessage(isMLMode ? 'ML AI thinking...' : 'Bot thinking...');
        
        try {
            const endpoint = isMLMode ? (gameState.mlMode === 'fast' ? '/get_ml_move' : '/get_hybrid_move') : '/get_bot_move';
            const body = {
                fen: getCurrentFEN()
            };
            
            if (isMLMode) {
                if (gameState.mlMode === 'fast') {
                    body.depth = 1;
                } else {
                    body.difficulty = gameState.difficulty;
                    body.ml_weight = 0.7;
                }
            } else {
                body.difficulty = gameState.difficulty;
            }
            
            const response = await fetch(endpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body)
            });
            
            const data = await response.json();
            if (data.error) throw new Error(data.error);
            
            console.log(`${isMLMode ? 'ML' : 'Bot'} move:`, data.from_square, '->', data.to_square);
            
            // DON'T play sound here - let makeMove handle all sounds
            // This way knight moves will still play horse sound even when bot moves knight
            
            await makeMove(data.from_square, data.to_square, data.promotion);
            
        } catch (error) {
            console.error('Error getting AI move:', error);
            SoundManager.play('warning');
            showMessage('AI error: ' + error.message);
            await makeRandomMove();
        }
    }

    // Fallback: make random move
    async function makeRandomMove() {
        try {
            const response = await fetch('/get_legal_moves', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ fen: getCurrentFEN() })
            });
            
            const data = await response.json();
            if (data.error || !data.legal_moves || data.legal_moves.length === 0) {
                throw new Error('No legal moves available');
            }
            
            const randomMove = data.legal_moves[Math.floor(Math.random() * data.legal_moves.length)];
            const from = randomMove.substring(0, 2);
            const to = randomMove.substring(2, 4);
            
            // DON'T play sound here - let makeMove handle all sounds
            await makeMove(from, to);
        } catch (error) {
            console.error('Error making random move:', error);
            SoundManager.play('warning');
            showMessage('AI cannot move');
        }
    }

    // Drag start handler
    function onDragStart(source, piece, position, orientation) {
        if (gameState.isGameOver) return false;
        
        if (gameState.gameMode === 'vs-bot' || gameState.gameMode === 'vs-ml') {
            const pieceColor = piece.charAt(0);
            const playerColor = gameState.playerSide.charAt(0);
            if (pieceColor !== playerColor) return false;
        }
        
        const pieceColor = piece.charAt(0);
        if ((pieceColor === 'w' && !gameState.isWhiteTurn) ||
            (pieceColor === 'b' && gameState.isWhiteTurn)) {
            return false;
        }
        
        return true;
    }

    // Drop handler
    async function onDrop(source, target, piece, newPos, oldPos, orientation) {
        clearSelection();
        const success = await makeMove(source, target);
        return success ? true : 'snapback';
    }

    // Snap end handler
    function onSnapEnd() {
        gameState.board.position(gameState.currentFen);
    }

    // Get current FEN
    function getCurrentFEN() {
        if (gameState.currentFen === 'start') {
            return 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';
        }
        return gameState.currentFen;
    }

    // Update game status display
    function updateGameStatus(data) {
        let statusText = `${gameState.isWhiteTurn ? 'White' : 'Black'} to move`;
        
        if (data.checkmate) {
            statusText = `Checkmate! ${gameState.isWhiteTurn ? 'Black' : 'White'} wins!`;
        } else if (data.stalemate) {
            statusText = 'Stalemate! Game drawn.';
        } else if (data.draw) {
            statusText = 'Game drawn.';
        } else if (data.check) {
            statusText = `${gameState.isWhiteTurn ? 'Black' : 'White'} is in check!`;
        }
        
        $('#status').text(statusText);
    }

    // Show game over message
    function showGameOverMessage(data) {
        let message = '';
        
        if (data.checkmate) {
            message = `🎉 Checkmate! ${gameState.isWhiteTurn ? 'Black' : 'White'} wins! 🎉`;
        } else if (data.stalemate) {
            message = '🤝 Stalemate! Game drawn. 🤝';
        } else if (data.draw) {
            message = '🤝 Game drawn. 🤝';
        }
        
        $('#game-over').html(`<h3>Game Over!</h3><p>${message}</p>`).removeClass('hidden');
    }

    // Update move history display
    function updateMoveHistory() {
        const $moveList = $('#move-list');
        $moveList.empty();
        
        for (let i = 0; i < gameState.moveHistory.length; i += 2) {
            const moveNumber = Math.floor(i / 2) + 1;
            const whiteMove = gameState.moveHistory[i];
            const blackMove = gameState.moveHistory[i + 1];
            
            const moveDiv = $('<div>').addClass('move-entry');
            
            if (whiteMove) {
                $('<span>').addClass('move-number').text(`${moveNumber}.`).appendTo(moveDiv);
                $('<span>').addClass('move white-move').text(whiteMove.move).appendTo(moveDiv);
            }
            
            if (blackMove) {
                $('<span>').addClass('move black-move').text(blackMove.move).appendTo(moveDiv);
            }
            
            $moveList.append(moveDiv);
        }
        
        $moveList.scrollTop($moveList[0].scrollHeight);
    }

    // Get move notation
    function getMoveNotation(from, to, promotion = null) {
        if (promotion) {
            return `${from}→${to}(${promotion.toUpperCase()})`;
        }
        return `${from}→${to}`;
    }

    // Show message with optional warning sound
    function showMessage(message) {
        const $error = $('#error-message');
        $error.text(message).removeClass('hidden');
        
        // Play warning for error messages
        if (message.includes('Invalid') || message.includes('Error') || 
            message.includes('cannot') || message.includes('over') ||
            message.includes("not your turn") || message.includes("AI's turn")) {
            SoundManager.play('warning');
        }
        
        setTimeout(() => $error.addClass('hidden'), 3000);
    }

    // Update control buttons
    function updateControlButtons() {
        $('#undo-btn').prop('disabled', gameState.fenHistory.length === 0);
    }

    // Setup event listeners for buttons
    function setupEventListeners() {
        // Mode buttons
        $('#two-player-btn').click(function() {
            setGameMode('two-player');
        });
        
        $('#vs-bot-btn').click(function() {
            setGameMode('vs-bot');
        });
        
        $('#vs-ml-btn').click(function() {
            setGameMode('vs-ml');
        });
        
        // Control buttons
        $('#new-game-btn').click(startNewGame);
        $('#flip-board-btn').click(flipBoard);
        $('#undo-btn').click(undoMove);
        $('#flip-sides-btn').click(flipPlayerSide);
        
        // Difficulty buttons
        $('.diff-btn').click(function() {
            const level = $(this).data('level');
            setDifficulty(level);
        });
        
        // ML mode buttons
        $('#ml-fast-btn').click(function() {
            gameState.mlMode = 'fast';
            $('.ml-mode button').removeClass('active');
            $(this).addClass('active');
            SoundManager.play('move');
            showMessage('ML Fast mode: Immediate evaluation');
        });
        
        $('#ml-deep-btn').click(function() {
            gameState.mlMode = 'deep';
            $('.ml-mode button').removeClass('active');
            $(this).addClass('active');
            SoundManager.play('move');
            showMessage('ML Deep mode: Hybrid search with ML');
        });
        
        // Sound toggle button
        $('#toggle-sound-btn').click(function() {
            const isEnabled = SoundManager.toggle();
            const $btn = $(this);
            
            if (isEnabled) {
                $btn.removeClass('muted').html('<i class="fas fa-volume-up"></i> Sound On');
                SoundManager.play('move'); // Test sound
            } else {
                $btn.addClass('muted').html('<i class="fas fa-volume-mute"></i> Sound Off');
            }
        });
        
        // Volume slider
        $('#volume-slider').on('input', function() {
            const volume = parseFloat($(this).val());
            SoundManager.setVolume(volume);
        });
    }

    // Set game mode
    function setGameMode(mode) {
        gameState.gameMode = mode;
        
        // Update UI
        $('#two-player-btn, #vs-bot-btn, #vs-ml-btn').removeClass('active');
        $(`#${mode === 'two-player' ? 'two-player-btn' : mode === 'vs-bot' ? 'vs-bot-btn' : 'vs-ml-btn'}`).addClass('active');
        
        // Show/hide controls
        if (mode === 'vs-ml') {
            $('.ml-controls').removeClass('hidden');
            $('.bot-controls').addClass('hidden');
            $('.side-controls').removeClass('hidden');
        } else if (mode === 'vs-bot') {
            $('.bot-controls').removeClass('hidden');
            $('.ml-controls').addClass('hidden');
            $('.side-controls').removeClass('hidden');
        } else {
            $('.bot-controls, .ml-controls, .side-controls').addClass('hidden');
        }
        
        updateSideInfo();
        
        // Save mode
        localStorage.setItem('chess-mode', mode);
        
        SoundManager.play('move');
        
        // If vs ML/bot and it's not player's turn, make AI move
        if (mode === 'vs-ml' || mode === 'vs-bot') {
            if ((gameState.playerSide === 'white' && !gameState.isWhiteTurn) ||
                (gameState.playerSide === 'black' && gameState.isWhiteTurn)) {
                setTimeout(getBotOrMLMove, 500);
            }
        }
    }

    // Set difficulty
    function setDifficulty(level) {
        gameState.difficulty = level;
        $('.diff-btn').removeClass('active');
        $(`.diff-btn[data-level="${level}"]`).addClass('active');
        localStorage.setItem('bot-difficulty', level);
        SoundManager.play('move');
        showMessage(`Difficulty set to level ${level}`);
    }

    // Flip player side
    function flipPlayerSide() {
        gameState.playerSide = gameState.playerSide === 'white' ? 'black' : 'white';
        updateSideInfo();
        SoundManager.play('move');
        
        if (gameState.gameMode === 'vs-bot' || gameState.gameMode === 'vs-ml') {
            if ((gameState.playerSide === 'white' && !gameState.isWhiteTurn) ||
                (gameState.playerSide === 'black' && gameState.isWhiteTurn)) {
                setTimeout(getBotOrMLMove, 500);
            }
        }
    }

    // Update side info
    function updateSideInfo() {
        const sideText = gameState.gameMode === 'two-player' 
            ? 'Two Player Mode'
            : `You are playing as ${gameState.playerSide.charAt(0).toUpperCase() + gameState.playerSide.slice(1)}`;
        $('#side-info').text(sideText);
    }

    // Start new game
    function startNewGame() {
        gameState.board.position('start');
        gameState.currentFen = 'start';
        gameState.selectedSquare = null;
        gameState.validMoves = [];
        gameState.moveHistory = [];
        gameState.fenHistory = [];
        gameState.isWhiteTurn = true;
        gameState.isGameOver = false;
        
        updateGameStatus({});
        updateMoveHistory();
        clearSelection();
        updateControlButtons();
        $('#game-over').addClass('hidden');
        
        if (window.hidePromotionModal) window.hidePromotionModal();
        if (window.resetPromotionState) window.resetPromotionState();
        
        SoundManager.play('move');
        
        if ((gameState.gameMode === 'vs-ml' || gameState.gameMode === 'vs-bot') && gameState.playerSide === 'black') {
            setTimeout(getBotOrMLMove, 500);
        }
    }

    // Flip board
    function flipBoard() {
        gameState.board.flip();
        gameState.boardFlipped = !gameState.boardFlipped;
        SoundManager.play('move');
    }

    // Undo move
    function undoMove() {
        if (gameState.fenHistory.length === 0) {
            SoundManager.play('warning');
            showMessage('No moves to undo');
            return;
        }
        
        console.log('Undoing move, current mode:', gameState.gameMode, 'fenHistory length:', gameState.fenHistory.length);
        
        if (gameState.gameMode === 'vs-bot' || gameState.gameMode === 'vs-ml') {
            const playerColor = gameState.playerSide.charAt(0);
            const currentTurnColor = gameState.isWhiteTurn ? 'w' : 'b';
            
            if (playerColor === currentTurnColor) {
                undoSingleMove();
            } else {
                if (gameState.fenHistory.length >= 2) {
                    undoTwoMoves();
                } else {
                    undoSingleMove();
                }
            }
        } else {
            undoSingleMove();
        }
        
        if (window.hidePromotionModal) window.hidePromotionModal();
        SoundManager.play('move');
        showMessage('Move undone');
    }

    // Helper function to undo a single move
    function undoSingleMove() {
        if (gameState.fenHistory.length === 0) return;
        
        const lastFen = gameState.fenHistory.pop();
        gameState.board.position(lastFen);
        gameState.currentFen = lastFen;
        gameState.isWhiteTurn = !gameState.isWhiteTurn;
        gameState.isGameOver = false;
        
        if (gameState.moveHistory.length > 0) {
            gameState.moveHistory.pop();
        }
        
        updateGameStatus({});
        updateMoveHistory();
        clearSelection();
        updateControlButtons();
        $('#game-over').addClass('hidden');
    }

    // Helper function to undo two moves
    function undoTwoMoves() {
        if (gameState.fenHistory.length < 2) {
            undoSingleMove();
            return;
        }
        
        gameState.fenHistory.pop();
        const lastFen = gameState.fenHistory.pop();
        gameState.board.position(lastFen);
        gameState.currentFen = lastFen;
        
        const playerColor = gameState.playerSide.charAt(0);
        gameState.isWhiteTurn = (playerColor === 'w');
        gameState.isGameOver = false;
        
        if (gameState.moveHistory.length > 0) gameState.moveHistory.pop();
        if (gameState.moveHistory.length > 0) gameState.moveHistory.pop();
        
        updateGameStatus({});
        updateMoveHistory();
        clearSelection();
        updateControlButtons();
        $('#game-over').addClass('hidden');
    }

    // Load saved state
    function loadSavedState() {
        const savedMode = localStorage.getItem('chess-mode');
        if (savedMode) {
            setGameMode(savedMode);
        } else {
            setGameMode('vs-bot');
        }
        
        const savedMLMode = localStorage.getItem('ml-mode');
        if (savedMLMode) {
            gameState.mlMode = savedMLMode;
            if (savedMLMode === 'fast') {
                $('#ml-fast-btn').addClass('active').siblings().removeClass('active');
            } else {
                $('#ml-deep-btn').addClass('active').siblings().removeClass('active');
            }
        }
        
        const savedDifficulty = localStorage.getItem('bot-difficulty');
        if (savedDifficulty) {
            gameState.difficulty = parseInt(savedDifficulty);
            $(`.diff-btn[data-level="${savedDifficulty}"]`).addClass('active')
                .siblings().removeClass('active');
        }
        
        // Load sound preference
        const soundEnabled = localStorage.getItem('sound-enabled');
        if (soundEnabled === 'false') {
            SoundManager.enabled = false;
            $('#toggle-sound-btn').addClass('muted').html('<i class="fas fa-volume-mute"></i> Sound Off');
        }
        
        // Load volume preference
        const savedVolume = localStorage.getItem('sound-volume');
        if (savedVolume) {
            SoundManager.setVolume(parseFloat(savedVolume));
            $('#volume-slider').val(savedVolume);
        }
    }

    // === MAIN INITIALIZATION ===
    
    setupMobileOptimizations();
    $(window).on('resize', optimizeBoardForMobile);
    
    // Initialize the game
    initBoard();
    setupEventListeners();
    updateGameStatus({});
    updateControlButtons();
    
    // Load saved state
    loadSavedState();
    
    // Optimize board for mobile after initialization
    setTimeout(optimizeBoardForMobile, 100);
});