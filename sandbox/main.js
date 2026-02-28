document.addEventListener('DOMContentLoaded', () => {
  const game = new Game();
  let winShown = false;
  let touchStartX = 0;
  let touchStartY = 0;

  // Render functions
  function renderBoard(game) {
    const gridEl = document.getElementById('grid');
    const board = game.getBoard();

    // Compute tile dimensions dynamically
    const gridW = gridEl.clientWidth;
    const gridH = gridEl.clientHeight;
    const padding = gridW * (12 / 480);
    const gap = gridW * (12 / 480);
    const cellW = (gridW - 2 * padding - 3 * gap) / 4;
    const cellH = (gridH - 2 * padding - 3 * gap) / 4;

    // Remove all existing tiles
    const existingTiles = gridEl.querySelectorAll('.tile');
    existingTiles.forEach(tile => tile.remove());

    // Create tiles for non-zero cells
    for (let row = 0; row < 4; row++) {
      for (let col = 0; col < 4; col++) {
        const value = board[row][col];
        if (value === 0) continue;

        const tile = document.createElement('div');
        const tileClass = value > 2048 ? 'tile-super' : `tile-${value}`;
        tile.className = `tile ${tileClass}`;
        tile.textContent = value;

        tile.style.position = 'absolute';
        tile.style.width = cellW + 'px';
        tile.style.height = cellH + 'px';
        tile.style.left = (padding + col * (cellW + gap)) + 'px';
        tile.style.top = (padding + row * (cellH + gap)) + 'px';

        gridEl.appendChild(tile);
      }
    }
  }

  function renderScore(game) {
    document.getElementById('score').textContent = game.getScore();
    document.getElementById('best-score').textContent = game.getBestScore();
  }

  function showOverlay(message) {
    const overlay = document.getElementById('overlay');
    const overlayMessage = document.getElementById('overlay-message');
    overlayMessage.textContent = message;
    overlay.classList.remove('hidden');
  }

  function hideOverlay() {
    const overlay = document.getElementById('overlay');
    overlay.classList.add('hidden');
  }

  function handleMove(direction) {
    const result = game.move(direction);
    if (!result.moved) return;

    renderBoard(game);

    // Add animation class to newly spawned tile
    if (result.spawned) {
      const gridEl = document.getElementById('grid');
      const gridW = gridEl.clientWidth;
      const padding = gridW * (12 / 480);
      const gap = gridW * (12 / 480);
      const cellW = (gridW - 2 * padding - 3 * gap) / 4;

      const tiles = gridEl.querySelectorAll('.tile');
      for (const tile of tiles) {
        const tileLeft = parseFloat(tile.style.left);
        const tileTop = parseFloat(tile.style.top);
        const expectedLeft = padding + result.spawned.col * (cellW + gap);
        const expectedTop = padding + result.spawned.row * (cellW + gap);

        if (Math.abs(tileLeft - expectedLeft) < 1 && Math.abs(tileTop - expectedTop) < 1) {
          tile.classList.add('tile-new');
          setTimeout(() => {
            tile.classList.remove('tile-new');
          }, 200);
          break;
        }
      }
    }

    renderScore(game);

    // Check win condition
    if (game.isWon() && !winShown) {
      winShown = true;
      showOverlay('You Win! 🎉');
    }

    // Check game over condition
    if (game.isOver()) {
      showOverlay('Game Over!');
    }
  }

  // Event listeners
  document.addEventListener('keydown', (e) => {
    let direction = null;
    switch (e.key) {
      case 'ArrowLeft':
        direction = 'left';
        break;
      case 'ArrowRight':
        direction = 'right';
        break;
      case 'ArrowUp':
        direction = 'up';
        break;
      case 'ArrowDown':
        direction = 'down';
        break;
    }

    if (direction) {
      e.preventDefault();
      handleMove(direction);
    }
  });

  const gridContainer = document.getElementById('grid-container');
  gridContainer.addEventListener('touchstart', (e) => {
    touchStartX = e.touches[0].clientX;
    touchStartY = e.touches[0].clientY;
  });

  gridContainer.addEventListener('touchend', (e) => {
    const touchEndX = e.changedTouches[0].clientX;
    const touchEndY = e.changedTouches[0].clientY;
    const dx = touchEndX - touchStartX;
    const dy = touchEndY - touchStartY;
    const absDx = Math.abs(dx);
    const absDy = Math.abs(dy);

    // Require one axis to be significantly larger (2x) and exceed 30px threshold to avoid diagonal swipes
    if (absDx > absDy * 1.25 && absDx > 30) {
      handleMove(dx > 0 ? 'right' : 'left');
    } else if (absDy > absDx * 1.25 && absDy > 30) {
      handleMove(dy > 0 ? 'down' : 'up');
    }
  });

  function resetGame() {
    game.reset();
    hideOverlay();
    winShown = false;
    renderBoard(game);
    renderScore(game);
  }

  document.getElementById('new-game-btn').addEventListener('click', resetGame);
  document.getElementById('try-again-btn').addEventListener('click', resetGame);

  // Initial render
  renderBoard(game);
  renderScore(game);
});
