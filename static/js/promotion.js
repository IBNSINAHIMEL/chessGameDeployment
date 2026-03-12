// promotion.js - Simplified and working version
$(document).ready(function() {
    console.log('Promotion module loaded');
    
    let promotionResolve = null;
    let promotionReject = null;
    
    // Initialize promotion modal
    function initPromotionModal() {
        console.log('Initializing promotion modal');
        
        // Set up click handlers for promotion buttons
        $('.promotion-btn').off('click').on('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            
            const piece = $(this).data('piece');
            console.log('Promotion piece selected:', piece);
            
            // Resolve the promise with the selected piece
            if (promotionResolve) {
                promotionResolve(piece);
                resetPromotionState();
                hidePromotionModal();
            }
        });
        
        // Handle clicking outside the modal (auto-select queen)
        $('#promotion-modal').off('click').on('click', function(e) {
            if (e.target === this) {
                console.log('Clicked outside modal, auto-selecting queen');
                if (promotionResolve) {
                    promotionResolve('q');
                }
                resetPromotionState();
                hidePromotionModal();
            }
        });
    }
    
    function showPromotionModal(color, from, to) {
        return new Promise((resolve, reject) => {
            console.log('showPromotionModal called, color:', color, 'from:', from, 'to:', to);
            
            // Store the resolve/reject functions
            promotionResolve = resolve;
            promotionReject = reject;
            
            // Update piece images based on color
            const piecePrefix = color === 'w' ? 'w' : 'b';
            const titleColor = color === 'w' ? 'White' : 'Black';
            
            // Update images
            $('#promotion-queen img').attr('src', `/static/img/chesspieces/wikipedia/${piecePrefix}Q.png`);
            $('#promotion-rook img').attr('src', `/static/img/chesspieces/wikipedia/${piecePrefix}R.png`);
            $('#promotion-bishop img').attr('src', `/static/img/chesspieces/wikipedia/${piecePrefix}B.png`);
            $('#promotion-knight img').attr('src', `/static/img/chesspieces/wikipedia/${piecePrefix}N.png`);
            
            // Update title
            $('#promotion-title').text(`${titleColor} Pawn Promotion - Choose a piece:`);
            
            // Show modal
            $('#promotion-modal').removeClass('hidden');
            console.log('Promotion modal shown');
        });
    }
    
    function hidePromotionModal() {
        console.log('Hiding promotion modal');
        $('#promotion-modal').addClass('hidden');
    }
    
    function resetPromotionState() {
        promotionResolve = null;
        promotionReject = null;
    }
    
    // Initialize on document ready
    initPromotionModal();
    
    // Expose functions globally
    window.showPromotionModal = showPromotionModal;
    window.hidePromotionModal = hidePromotionModal;
    window.resetPromotionState = resetPromotionState;
    
    console.log('Promotion module ready');
});