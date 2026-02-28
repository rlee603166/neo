class Game {
  constructor() {
    this.board = Array(4).fill(null).map(() => Array(4).fill(0));
    this.score = 0;
    this.bestScore = parseInt(localStorage.getItem('best2048') || '0', 10);
    this._spawnTile();
    this._spawnTile();
  }

  reset() {
    this.board = Array(4).fill(null).map(() => Array(4).fill(0));
    this.score = 0;
    this._spawnTile();
    this._spawnTile();
  }

  getBoard() {
    return this.board.map(row => [...row]);
  }

  getScore() {
    return this.score;
  }

  getBestScore() {
    return this.bestScore;
  }

  isWon() {
    for (let row = 0; row < 4; row++) {
      for (let col = 0; col < 4; col++) {
        if (this.board[row][col] === 2048) {
          return true;
        }
      }
    }
    return false;
  }

  isOver() {
    // Check if there are empty cells
    for (let row = 0; row < 4; row++) {
      for (let col = 0; col < 4; col++) {
        if (this.board[row][col] === 0) {
          return false;
        }
      }
    }

    // Check for adjacent equal cells horizontally
    for (let row = 0; row < 4; row++) {
      for (let col = 0; col < 3; col++) {
        if (this.board[row][col] === this.board[row][col + 1] && this.board[row][col] !== 0) {
          return false;
        }
      }
    }

    // Check for adjacent equal cells vertically
    for (let row = 0; row < 3; row++) {
      for (let col = 0; col < 4; col++) {
        if (this.board[row][col] === this.board[row + 1][col] && this.board[row][col] !== 0) {
          return false;
        }
      }
    }

    return true;
  }

  move(direction) {
    // Save original board state
    const originalBoard = this.board.map(row => [...row]);

    // Rotate to make direction "left"
    let rotations = 0;
    if (direction === 'left') {
      rotations = 0;
    } else if (direction === 'right') {
      rotations = 2;
    } else if (direction === 'up') {
      rotations = 3;
    } else if (direction === 'down') {
      rotations = 1;
    }

    this._rotateBoard(rotations);

    // Slide all rows left
    let totalScoreGain = 0;
    for (let row = 0; row < 4; row++) {
      const result = this._slideRow(this.board[row]);
      this.board[row] = result.newRow;
      totalScoreGain += result.scoreGain;
    }

    // Rotate back
    const rotateBack = (4 - rotations) % 4;
    this._rotateBoard(rotateBack);

    // Check if board changed
    let moved = false;
    for (let row = 0; row < 4; row++) {
      for (let col = 0; col < 4; col++) {
        if (this.board[row][col] !== originalBoard[row][col]) {
          moved = true;
          break;
        }
      }
      if (moved) break;
    }

    let spawned = null;
    if (moved) {
      this.score += totalScoreGain;
      if (this.score > this.bestScore) {
        this.bestScore = this.score;
        localStorage.setItem('best2048', this.bestScore.toString());
      }
      spawned = this._spawnTile();
    }

    return { moved, spawned };
  }

  _spawnTile() {
    // Find all empty cells
    const emptyCells = [];
    for (let row = 0; row < 4; row++) {
      for (let col = 0; col < 4; col++) {
        if (this.board[row][col] === 0) {
          emptyCells.push({ row, col });
        }
      }
    }

    if (emptyCells.length === 0) {
      return null;
    }

    // Pick a random empty cell
    const cell = emptyCells[Math.floor(Math.random() * emptyCells.length)];

    // 90% chance for 2, 10% chance for 4
    const value = Math.random() < 0.9 ? 2 : 4;

    this.board[cell.row][cell.col] = value;

    return { row: cell.row, col: cell.col, value };
  }

  _slideRow(row) {
    // Make a copy to work with
    let arr = [...row];

    // Step 1: Compact non-zeros to the left
    arr = arr.filter(val => val !== 0);

    // Step 2: Scan left to right for merges
    // In 2048, a merged tile cannot merge again in the same move
    const mergedAt = [];
    let scoreGain = 0;
    for (let i = 0; i < arr.length - 1; i++) {
      if (arr[i] === arr[i + 1] && arr[i] !== 0) {
        arr[i] *= 2;
        scoreGain += arr[i];
        arr[i + 1] = 0; // Mark as zero instead of splicing
        mergedAt.push(i);
        i++; // Skip the next element since we just merged it
      }
    }

    // Step 3: Compact non-zeros again
    arr = arr.filter(val => val !== 0);

    // Step 4: Pad with zeros to length 4
    while (arr.length < 4) {
      arr.push(0);
    }

    return { newRow: arr, scoreGain, mergedAt };
  }

  _rotateBoard(times) {
    times = ((times % 4) + 4) % 4;

    for (let t = 0; t < times; t++) {
      // Rotate clockwise: transpose then reverse each row
      // Or: new[row][col] = old[4-1-col][row]
      const newBoard = Array(4).fill(null).map(() => Array(4).fill(0));

      for (let row = 0; row < 4; row++) {
        for (let col = 0; col < 4; col++) {
          newBoard[col][3 - row] = this.board[row][col];
        }
      }

      this.board = newBoard;
    }
  }
}

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
  module.exports = Game;
}
