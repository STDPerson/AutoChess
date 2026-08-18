import pyautogui
import time
import keyboard
import urllib.request
import json
import sys
import os
import cv2
import mss
import numpy as np
import tkinter as tk
import chess

# --- GLOBAL VARIABLES ---
bot_aktif = False
model_ai_terpilih = ""
board_rect = {'left': 0, 'top': 0, 'width': 0, 'height': 0}
kotak_w = 0
kotak_h = 0
player_color = "White"

prev_bgr = None
last_frame_bgr = None
stable_frames = 0
internal_board = None
last_fen = None
terakhir_mouse_pos = None
absolute_starting_bgr = None

class ESPOverlay:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Chess ESP")
        self.root.attributes("-transparentcolor", "white")
        self.root.attributes("-topmost", True)
        self.root.overrideredirect(True)
        self.root.geometry(f"{self.root.winfo_screenwidth()}x{self.root.winfo_screenheight()}+0+0")
        
        self.canvas = tk.Canvas(self.root, bg="white", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

    def update_esp(self, detections):
        self.canvas.delete("all")
        
        # Draw 8x8 grid for both empty and occupied squares
        if board_rect['width'] > 0:
            for row in range(8):
                for col in range(8):
                    x = board_rect['left'] + int(col*kotak_w)
                    y = board_rect['top'] + int(row*kotak_h)
                    self.canvas.create_rectangle(x, y, x+int(kotak_w), y+int(kotak_h), outline="gray", width=1, dash=(2,2))
        
        if not detections: return
        
        for det in detections:
            x, y, w, h = det['x'], det['y'], det['w'], det['h']
            label = det['label']
            color_label = det.get('color_label', '')
            
            color = "green" if color_label == "White" else "red"
            self.canvas.create_rectangle(x, y, x+w, y+h, outline=color, width=2)
            self.canvas.create_text(x + w - 5, y + 5, text=label, fill=color, anchor=tk.NE, font=("Arial", 8, "bold"))

    def clear(self):
        self.canvas.delete("all")
        self.root.update()

def pixel_idx_to_coord(row, col):
    if player_color == "Black":
        col = 7 - col
        row = 7 - row
    rank = 8 - row
    file_char = chr(ord('a') + col)
    return f"{file_char}{rank}"

def scan_board(is_validation=False):
    global player_color, prev_bgr, last_frame_bgr, stable_frames, internal_board, last_fen, absolute_starting_bgr
    
    with mss.MSS() as sct:
        monitor = {"top": int(board_rect['top']), "left": int(board_rect['left']), "width": int(board_rect['width']), "height": int(board_rect['height'])}
        img = np.array(sct.grab(monitor))
        gray = cv2.cvtColor(img, cv2.COLOR_BGRA2GRAY)
        bgr = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        
        if is_validation:
            # CALIBRATION BASED STRICTLY ON COLOR BRIGHTNESS
            h, w = gray.shape
            row_h = int(h / 8)
            
            # Extract top 2 rows and bottom 2 rows
            top_2_rows = gray[0:2*row_h, 0:w]
            bottom_2_rows = gray[6*row_h:8*row_h, 0:w]
            
            top_brightness = np.mean(top_2_rows)
            bottom_brightness = np.mean(bottom_2_rows)
            
            # In chess, White pieces are always brighter than Black pieces.
            if bottom_brightness > top_brightness:
                player_color = "White"
            else:
                player_color = "Black"
                
            print(f"[Vision] Color Profile -> Top Brightness: {top_brightness:.1f}, Bottom Brightness: {bottom_brightness:.1f}")
            print(f"[Vision] Detected you are playing as: {player_color}")
            
            internal_board = chess.Board() # Standard starting position
            absolute_starting_bgr = bgr.copy()
            prev_bgr = absolute_starting_bgr.copy()
            last_frame_bgr = bgr.copy()
            
            # Automatically succeeds as it doesn't use shape matching
            return True, None
            
        else:
            # --- LOGICAL STATE TRACKING (0ms AI Motion Sensor) ---
            if prev_bgr is None:
                if absolute_starting_bgr is not None:
                    prev_bgr = absolute_starting_bgr.copy()
                else:
                    prev_bgr = bgr.copy()
                
            if last_frame_bgr is not None:
                motion_diff = cv2.absdiff(bgr, last_frame_bgr)
                if np.mean(motion_diff) < 2:
                    stable_frames += 1
                else:
                    stable_frames = 0
            last_frame_bgr = bgr.copy()
            
            if stable_frames >= 2:
                diff = cv2.absdiff(bgr, prev_bgr)
                diff_max = np.max(diff, axis=2) # Get the highest difference across B, G, or R channels
                changed_squares = set()
                
                for row in range(8):
                    for col in range(8):
                        # Extract the center of the square (ignoring 15% margins)
                        x1 = int(col * kotak_w + kotak_w*0.15)
                        y1 = int(row * kotak_h + kotak_h*0.15)
                        x2 = int((col+1) * kotak_w - kotak_w*0.15)
                        y2 = int((row+1) * kotak_h - kotak_h*0.15)
                        
                        sq_diff = diff_max[y1:y2, x1:x2]
                        # NEW SENSITIVITY FORMULA (ANTI-CREAM COLOR COLLISION):
                        # If at least 20 pixels changed drastically (difference > 30)
                        # This ensures small pieces moving on light squares are 100% detected!
                        if np.sum(sq_diff > 30) > 20:
                            changed_squares.add(pixel_idx_to_coord(row, col))
                            
                if len(changed_squares) > 0:
                    best_move = None
                    # Find which legal move exactly caused these squares to change
                    for move in internal_board.legal_moves:
                        uci = move.uci()
                        move_sqs = {uci[:2], uci[2:4]}
                        
                        # Special rule (Castling)
                        if internal_board.is_castling(move):
                            if uci == 'e1g1': move_sqs.update(['h1', 'f1'])
                            elif uci == 'e1c1': move_sqs.update(['a1', 'd1'])
                            elif uci == 'e8g8': move_sqs.update(['h8', 'f8'])
                            elif uci == 'e8c8': move_sqs.update(['a8', 'd8'])
                            
                        # Special rule (En Passant)
                        if internal_board.is_en_passant(move):
                            cap_sq = f"{uci[2]}{uci[1]}"
                            move_sqs.add(cap_sq)
                            
                        if move_sqs.issubset(changed_squares):
                            best_move = move
                            # Prioritize if the number of changed squares matches exactly
                            if len(move_sqs) == len(changed_squares):
                                break
                                
                    if best_move:
                        internal_board.push(best_move)
                        print(f"[Logic] ENEMY movement detected! Updating board: {best_move.uci()}")
                        prev_bgr = bgr.copy() # Update reference AFTER enemy move is processed
            
            fen = internal_board.fen()
            
            # Build detections for ESP (100% based on mathematical memory, error-proof)
            detections = []
            for sq, piece in internal_board.piece_map().items():
                sq_name = chess.square_name(sq)
                char = piece.symbol()
                p_map = {'p':'Pawn', 'r':'Rook', 'n':'Knight', 'b':'Bishop', 'q':'Queen', 'k':'King'}
                label = p_map.get(char.lower(), '')
                
                # Add color info (used by ESPOverlay to color the borders)
                color_label = "White" if char.isupper() else "Black"
                
                col = ord(sq_name[0]) - ord('a')
                row = 8 - int(sq_name[1])
                if player_color == "Black":
                    col = 7 - col
                    row = 7 - row
                    
                detections.append({
                    'x': board_rect['left'] + int(col*kotak_w),
                    'y': board_rect['top'] + int(row*kotak_h),
                    'w': int(kotak_w),
                    'h': int(kotak_h),
                    'label': label,
                    'color_label': color_label
                })
                
            # Prevent double execution if nothing has changed
            if fen == last_fen:
                return None, detections
            last_fen = fen
            
            # Only ask for Ollama's move IF it's our turn!
            if internal_board.turn == (chess.WHITE if player_color == "White" else chess.BLACK):
                return fen, detections
            else:
                return None, detections

def kalibrasi_dan_validasi():
    global board_rect, kotak_w, kotak_h
    while True:
        print("\nCHESSBOARD CALIBRATION")
        print("[!] WARNING: Perform this calibration ONLY when the board is in its starting position (no pieces moved)!")
        print("Hover the cursor exactly over the TOP-LEFT CORNER of the chessboard, then press ENTER.")
        input()
        tl = pyautogui.position()
        
        print("Hover the cursor exactly over the BOTTOM-RIGHT CORNER of the chessboard, then press ENTER.")
        input()
        br = pyautogui.position()
        
        board_rect = {
            'left': int(min(tl[0], br[0])), 
            'top': int(min(tl[1], br[1])),
            'width': int(abs(br[0] - tl[0])),
            'height': int(abs(br[1] - tl[1]))
        }
        
        if board_rect['width'] < 100 or board_rect['height'] < 100:
            print("[!] CALIBRATION FAILED: Selected area is too small.")
            continue
            
        kotak_w = board_rect['width'] / 8.0
        kotak_h = board_rect['height'] / 8.0
        
        print("\n[Vision] Reading piece colors to determine if you are White or Black...")
        scan_board(is_validation=True)
        print(f"[V] Calibration complete! Standard chessboard has been loaded into the bot's memory.")
        break

def coord_to_pixel(square_str):
    col = ord(square_str[0]) - ord('a')
    row = 8 - int(square_str[1])
    
    if player_color == "Black":
        col = 7 - col
        row = 7 - row
        
    x = board_rect['left'] + col * kotak_w + (kotak_w/2)
    y = board_rect['top'] + row * kotak_h + (kotak_h/2)
    return x, y

def minta_langkah_ai(fen):
    print(f"\n[AI Engine] Board Condition (FEN): {fen}")
    
    # Collect all legal moves to be injected into the AI
    board = chess.Board(fen)
    legal_moves = [move.uci() for move in board.legal_moves]
    legal_moves_str = ", ".join(legal_moves)
    
    # TACTICAL ANALYSIS: Help AI "predict" threats like a true chess engine
    in_danger = []
    opportunities = []
    enemy_color = not board.turn
    my_color = board.turn
    
    for sq in chess.SQUARES:
        piece = board.piece_at(sq)
        if piece:
            if piece.color == my_color:
                if board.is_attacked_by(enemy_color, sq):
                    in_danger.append(f"{piece.symbol()} at {chess.square_name(sq)}")
            else:
                if board.is_attacked_by(my_color, sq):
                    opportunities.append(f"{piece.symbol()} at {chess.square_name(sq)}")
                    
    tactics = "Tactical Analysis: "
    if board.is_check():
        tactics += "CRITICAL: Your King is IN CHECK! You must resolve the check! "
    if in_danger:
        tactics += f"WARNING: Your pieces [{', '.join(in_danger)}] are currently UNDER ATTACK by the enemy! Protect them or counter-attack! "
    if opportunities:
        tactics += f"OPPORTUNITY: You can attack or capture enemy pieces [{', '.join(opportunities)}]. "
    
    # Smart prompt: Force AI to comply with legal moves and provide strategic goals along with threat predictions
    prompt = f"Current chess board FEN is: {fen}. You are playing as {player_color}. {tactics}Your ultimate goal is to aggressively attack the enemy king to achieve CHECKMATE, while fiercely protecting your own king from any threats. The ONLY legal moves you can make right now are: [{legal_moves_str}]. Choose the BEST tactical move from this exact list to achieve your goal. Reply ONLY with the move in 4-character UCI format (e.g. {legal_moves[0] if legal_moves else 'e2e4'}) and nothing else."
    
    data_request = json.dumps({
        "model": model_ai_terpilih,
        "prompt": prompt,
        "stream": False
    }).encode('utf-8')
    
    try:
        print(f"[{model_ai_terpilih}] Thinking about the next move for {player_color}...")
        req = urllib.request.Request("http://localhost:11434/api/generate", data=data_request, headers={'Content-Type': 'application/json'})
        response = urllib.request.urlopen(req)
        result = json.loads(response.read().decode('utf-8'))
        langkah = result.get('response', '').strip().lower()
        
        import re
        match = re.search(r'([a-h][1-8][a-h][1-8])', langkah)
        if match:
            kandidat = match.group(1)
            # Strict validation: AI must not make illegal moves that violate chess rules!
            if kandidat in legal_moves:
                return kandidat
            else:
                print(f"[!] AI violated rules with an illegal move ({kandidat}). Forcing safe fallback...")
                return legal_moves[0] if legal_moves else None
        else:
            print(f"[!] AI returned an invalid format ({langkah}). Requesting engine fallback...")
            return legal_moves[0] if legal_moves else None
    except Exception as e:
        print(f"[X] Failed to connect to Ollama: {e}")
        return None

def toggle_bot():
    global bot_aktif, terakhir_mouse_pos
    bot_aktif = not bot_aktif
    status = "ACTIVE [ON]" if bot_aktif else "STOPPED [OFF] (Standby)"
    print(f"\n[System] Trigger pressed! Bot Status: {status}")
    
    if bot_aktif:
        terakhir_mouse_pos = pyautogui.position()
    else:
        if esp: esp.clear()

def ambil_model_ollama():
    print("Searching for Ollama models...")
    try:
        url = "http://localhost:11434/api/tags"
        response = urllib.request.urlopen(url)
        data = json.loads(response.read().decode('utf-8'))
        models = data.get('models', [])
        if not models: return None
        for i, model in enumerate(models):
            print(f"[{i + 1}] {model['name']}")
        while True:
            try:
                pilihan = int(input("> Enter the AI model number: "))
                if 1 <= pilihan <= len(models):
                    return models[pilihan - 1]['name']
            except ValueError:
                pass
    except Exception:
        return None

if __name__ == "__main__":
    model_ai_terpilih = ambil_model_ollama()
    if not model_ai_terpilih: exit()
    
    kalibrasi_dan_validasi()
    
    keyboard.add_hotkey('f10', toggle_bot)
    print("=================================================")
    print(f"[Bot] Ready to play automatically with: {model_ai_terpilih}")
    print("[*] Press 'F10' to Start / Stop.")
    print("=================================================\n")
    
    esp = ESPOverlay()
    
    try:
        while True:
            if bot_aktif:
                pos_sekarang = pyautogui.position()
                if terakhir_mouse_pos:
                    if abs(pos_sekarang[0] - terakhir_mouse_pos[0]) > 15 or abs(pos_sekarang[1] - terakhir_mouse_pos[1]) > 15:
                        print("[!] Cursor was moved manually. Bot deactivated!")
                        toggle_bot()
                        continue
                
                fen, detections = scan_board(is_validation=False)
                if detections is not None:
                    esp.update_esp(detections)
                
                if fen is not None:
                    langkah = minta_langkah_ai(fen)
                    if langkah:
                        print(f"[*] Executing move: {langkah}")
                        x1, y1 = coord_to_pixel(langkah[0:2])
                        x2, y2 = coord_to_pixel(langkah[2:4])
                        
                        pyautogui.moveTo(x1, y1, duration=0.2)
                        pyautogui.mouseDown()
                        time.sleep(0.1)
                        pyautogui.moveTo(x2, y2, duration=0.4)
                        pyautogui.mouseUp()
                        
                        terakhir_mouse_pos = pyautogui.position()
                        
                        # UPDATE INTERNAL MEMORY MANUALLY (NO NEED TO WAIT FOR SENSOR)
                        # This prevents the bot from hallucinating its own move as an enemy move
                        try:
                            move = chess.Move.from_uci(langkah)
                            if move in internal_board.legal_moves:
                                internal_board.push(move)
                                print(f"[*] Board memory updated with bot's move: {langkah}")
                        except Exception as e:
                            pass
                            
                        # Wait briefly for the AI/bot on screen to finish passing the turn
                        time.sleep(0.3)
                        
                esp.root.update()
                time.sleep(0.05)
            else:
                esp.root.update()
                time.sleep(0.1)
                
    except KeyboardInterrupt:
        print("\nProgram terminated.")