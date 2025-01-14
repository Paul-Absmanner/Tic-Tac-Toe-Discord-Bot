import discord
from discord import app_commands
from enum import Enum
from invinci_bot import InvinciBot

# Create a new environment variable

#TODO replace Placeholders with discord bot TOKEN and GUILD_ID from the discord channel
TOKEN="MTMyODc2MD..."
GUILD_ID=12345678

intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)


# ------------------------------------------------------
# 1) A small "Player" representation
# ------------------------------------------------------
class Symbol(Enum):
    X = "X"
    O = "O"
    NONE = " "

class Player:
    def __init__(self, symbol: Symbol):
        self.symbol = symbol.value
        self._other = None  # We'll assign this after creation

    @property
    def other(self):
        return self._other

    @other.setter
    def other(self, p):
        self._other = p


# ------------------------------------------------------
# 2) Board class that InvinciBot expects
# ------------------------------------------------------
class Board:
    """
    Wraps a 3x3 list board and provides the methods
    that InvinciBot.minimax requires.
    """
    def __init__(self, squares, move_history):
        # squares: 9-element list of ["X","O"," "]
        self.squares = squares[:]  # copy
        self.move_history = move_history[:]  # list of (row,col)

    def last_move(self):
        """Return the last (row,col) that was played, or (None,None)."""
        return self.move_history[-1] if self.move_history else (None, None)

    def has_winner(self):
        """Return 'X' or 'O' if there's a winner, else None."""
        wins = [
            (0, 1, 2), (3, 4, 5), (6, 7, 8),
            (0, 3, 6), (1, 4, 7), (2, 5, 8),
            (0, 4, 8), (2, 4, 6)
        ]
        for (a, b, c) in wins:
            if (self.squares[a] == self.squares[b] == self.squares[c] 
                and self.squares[a] in ["X", "O"]):
                return self.squares[a]
        return None

    @property
    def moves(self):
        """All moves made so far, for tie checking (9 means full)."""
        return self.move_history

    def get_legal_moves(self):
        """
        Return a list of (row, col) that are still free.
        Our squares array is a single 9-element list, so we map:
           index = row*3 + col
        """
        moves = []
        for idx, symbol in enumerate(self.squares):
            if symbol == " ":
                row, col = divmod(idx, 3)
                moves.append((row, col))
        return moves

    def make_move(self, row, col, symbol):
        """Mark squares[row*3+col] = symbol, add to history."""
        idx = row*3 + col
        self.squares[idx] = symbol
        self.move_history.append((row, col))


# ------------------------------------------------------
# 3) The TicTacToeGame to keep track of who is playing
#    and how we map the 9-element list onto the Board.
# ------------------------------------------------------
class TicTacToeGame:
    def __init__(self, player_x: discord.User, player_o: discord.User = None, ai_mode=False):
        # We store a 9-element list for the board
        self.board = [" "] * 9
        self.move_history = []
        self.player_x = player_x
        self.player_o = player_o
        self.ai_mode = ai_mode

        # We'll create an AI instance if in ai_mode
        # Minimax needs an object 'Player' with .symbol and .other
        self.playerX_obj = Player(Symbol.X)
        self.playerO_obj = Player(Symbol.O)
        # Link them
        self.playerX_obj.other = self.playerO_obj
        self.playerO_obj.other = self.playerX_obj

        # If AI mode is True, we set up InvinciBot for O
        self.ai = None
        if self.ai_mode:
            self.ai = InvinciBot(self.playerO_obj)  # O will be the AI

        self.current_player = self.player_x  # X starts
        self.winner = None

    def make_move(self, position: int, who: discord.User):
        """Apply a move (0..8) from the given player, if valid."""
        if position < 0 or position > 8:
            return False

        if self.board[position] != " ":
            return False

        # Determine symbol based on who
        symbol = "X" if who == self.player_x else "O"
        self.board[position] = symbol

        # Also track row,col in move_history
        row, col = divmod(position, 3)
        self.move_history.append((row, col))

        # Check if winner
        if self.check_winner():
            self.winner = who
        else:
            # Switch turn
            if self.ai_mode:
                # If the last move was from player_x (human),
                # next up might be the AI (player_o).
                if who == self.player_x:
                    self.current_player = None  # "AI's turn" signal
                else:
                    self.current_player = self.player_x
            else:
                self.current_player = self.player_o if who == self.player_x else self.player_x

        return True

    def check_winner(self):
        # Simple check for a winner
        wins = [
            (0, 1, 2), (3, 4, 5), (6, 7, 8),
            (0, 3, 6), (1, 4, 7), (2, 5, 8),
            (0, 4, 8), (2, 4, 6)
        ]
        for (a, b, c) in wins:
            if self.board[a] == self.board[b] == self.board[c] != " ":
                return True
        return False

    def is_draw(self):
        return (" " not in self.board) and (self.winner is None)

    def do_ai_move(self):
        """
        Called when it's AI's turn. We'll build a Board object
        from the current self.board, run minimax, and apply that move.
        """
        if not self.ai:
            return

        # Build a Board wrapper
        b = Board(self.board, self.move_history)
        move = self.ai.select_move(b)  # returns (row, col)

        if move == (None, None):
            return  # no moves left or something

        row, col = move
        position = row * 3 + col
        self.board[position] = "O"  # AI is O
        self.move_history.append(move)

        # Check winner
        if self.check_winner():
            self.winner = self.player_o
        else:
            # Next turn is X
            self.current_player = self.player_x


# ------------------------------------------------------
# 4) A Discord UI View with Buttons
# ------------------------------------------------------
class TicTacToeView(discord.ui.View):
    def __init__(self, game: TicTacToeGame, timeout=180):
        super().__init__(timeout=timeout)
        self.game = game
        self.update_buttons()

    def update_buttons(self):
        self.clear_items()
        for i in range(9):
            label = self.game.board[i] if self.game.board[i] != " " else "."
            disabled = (self.game.board[i] != " ") or (self.game.winner is not None)
            button = discord.ui.Button(
                label=label,
                style=discord.ButtonStyle.secondary,
                disabled=disabled,
                row=i // 3,
                custom_id=str(i)
            )
            button.callback = self.handle_click
            self.add_item(button)

    async def handle_click(self, interaction: discord.Interaction):
        # If there's a winner or draw, ignore clicks
        if self.game.winner or self.game.is_draw():
            await interaction.response.defer()
            return

        # If AI mode
        if self.game.ai_mode:
            # If current_player is None => it's AI's turn, ignore clicks
            if self.game.current_player is None:
                await interaction.response.defer()
                return

            # Must be X's turn (the human)
            if interaction.user != self.game.current_player:
                await interaction.response.defer()
                return

            position = int(interaction.data["custom_id"])
            success = self.game.make_move(position, interaction.user)
            self.update_buttons()

            if success:
                if self.game.winner:
                    content = f"{self.game.winner.mention} wins!"
                    for child in self.children:
                        child.disabled = True
                    await interaction.response.edit_message(content=content, view=self)
                    return
                elif self.game.is_draw():
                    content = "It's a draw!"
                    for child in self.children:
                        child.disabled = True
                    await interaction.response.edit_message(content=content, view=self)
                    return
                else:
                    # If still ongoing, do AI's turn
                    await interaction.response.defer()
                    self.game.do_ai_move()
                    self.update_buttons()
                    if self.game.winner:
                        content = "AI wins!"
                        for child in self.children:
                            child.disabled = True
                    elif self.game.is_draw():
                        content = "It's a draw!"
                        for child in self.children:
                            child.disabled = True
                    else:
                        if self.game.current_player is None:
                            content = "AI wins!"
                        else:
                            content = f"Next turn: {self.game.current_player.mention}"
                    await interaction.edit_original_response(content=content, view=self)
            else:
                await interaction.response.defer()

        else:
            # Human vs. Human
            if interaction.user != self.game.current_player:
                await interaction.response.defer()
                return

            position = int(interaction.data["custom_id"])
            success = self.game.make_move(position, interaction.user)
            self.update_buttons()

            if success:
                if self.game.winner:
                    content = f"{self.game.winner.mention} wins!"
                    for child in self.children:
                        child.disabled = True
                elif self.game.is_draw():
                    content = "It's a draw!"
                    for child in self.children:
                        child.disabled = True
                else:
                    content = f"Next turn: {self.game.current_player.mention}"
                await interaction.response.edit_message(content=content, view=self)
            else:
                await interaction.response.defer()


# ------------------------------------------------------
# 5) The Slash Commands
# ------------------------------------------------------
@tree.command(
    name="tictactoe",
    description="Play Tic-Tac-Toe with a friend or the minimax AI.",
    guild=discord.Object(id=GUILD_ID)
)
@app_commands.describe(
    mode="Choose 'ai' to play against minimax, or 'player' for a friend.",
    opponent="Mention a user if in 'player' mode"
)
async def tictactoe_command(
    interaction: discord.Interaction,
    mode: str,
    opponent: discord.Member = None
):
    """
    Example:
    /tictactoe mode:<ai|player> opponent:@somebody?
    """
    mode = mode.lower()
    if mode not in ("ai", "player"):
        await interaction.response.send_message("Mode must be 'ai' or 'player'.", ephemeral=True)
        return

    if mode == "ai":
        game = TicTacToeGame(
            player_x=interaction.user,
            player_o=None,
            ai_mode=True
        )
        content = (
            f"**Tic-Tac-Toe vs. Minimax AI**\n"
            f"Player X: {game.player_x.mention}\n"
            f"Player O: AI\n\n"
            f"Next turn: {game.current_player.mention}"
        )
    else:
        if opponent is None:
            await interaction.response.send_message("You must mention an opponent in 'player' mode.", ephemeral=True)
            return
        if opponent.bot:
            await interaction.response.send_message("Cannot challenge a bot in 'player' mode.", ephemeral=True)
            return
        game = TicTacToeGame(
            player_x=interaction.user,
            player_o=opponent,
            ai_mode=False
        )
        content = (
            f"**Tic-Tac-Toe Player vs. Player**\n"
            f"Player X: {game.player_x.mention}\n"
            f"Player O: {game.player_o.mention}\n\n"
            f"Next turn: {game.current_player.mention}"
        )

    view = TicTacToeView(game)
    await interaction.response.send_message(content=content, view=view)


@client.event
async def on_ready():
    print(f"Bot is ready. Logged in as {client.user}")

    guild = discord.Object(id=GUILD_ID)
    synced = await tree.sync(guild=guild)
    print("Slash commands synced.")
    for cmd in synced:
        print(f"- /{cmd.name}")


client.run(TOKEN)