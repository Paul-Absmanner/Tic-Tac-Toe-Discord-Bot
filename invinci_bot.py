# invinci_bot.py

import copy

class Choice():
    def __init__(self, move, value, depth):
        self.move = move
        self.value = value
        self.depth = depth

    def __str__(self):
        return f"{self.move}: {self.value}"

class InvinciBot():
    """
    A minimax-based AI for Tic-Tac-Toe.
    Expects 'board' objects that implement:
      - board.has_winner() -> returns the winning player symbol or None
      - board.last_move() -> returns the last (row, col) used
      - board.get_legal_moves() -> returns a list of (row, col) for empty spots
      - board.make_move(row, col, player)
      - board.moves -> list of all moves that have been made
    and also a 'current_player.other' reference for the opponent.
    """
    def __init__(self, player):
        # 'player' is a Player-like object with .symbol and .other
        self.player = player

    def minimax(self, board, is_max, current_player, depth):
        # Check if there's a winner or if it's a tie
        winner = board.has_winner()
        if winner == self.player.symbol:
            return Choice(board.last_move(), 10 - depth, depth)
        elif winner == current_player.other.symbol:
            return Choice(board.last_move(), -10 + depth, depth)
        elif len(board.moves) == 9:  # all squares filled => tie
            return Choice(board.last_move(), 0, depth)

        # Otherwise, evaluate all possible moves
        candidate_choices = []
        candidates = board.get_legal_moves()
        for (row, col) in candidates:
            newboard = copy.deepcopy(board)
            newboard.make_move(row, col, current_player.symbol)
            result = self.minimax(newboard, not is_max, current_player.other, depth + 1)
            # Overwrite the move with the actual one we just made
            result.move = newboard.last_move()
            candidate_choices.append(result)

        # Decide max/min choice depending on who's moving
        max_choice = None
        max_value = -100
        min_choice = None
        min_value = 100

        for choice in candidate_choices:
            if is_max and choice.value > max_value:
                max_choice = choice
                max_value = choice.value
            elif not is_max and choice.value < min_value:
                min_choice = choice
                min_value = choice.value

        if is_max:
            return max_choice
        else:
            return min_choice

    def select_move(self, board):
        # Start the recursion at depth=0, maximizing for self.player
        choice = self.minimax(board, True, self.player, 0)
        return choice.move
