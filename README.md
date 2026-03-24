# Shinobi Battle

A two-player, turn-based battle game where players perform real-world hand signs via webcam. A computer vision pipeline classifies signs and maps them to in-game jutsu (attacks, defenses, heals). The game runs online via WebRTC for video and WebSocket for game state.

## Architecture

```
├── config/game.yaml          ← All balance values & jutsu definitions
├── server/                   ← Python WebSocket server (authoritative game state)
│   ├── main.py               ← Entry point
│   ├── game_engine.py        ← Core gameplay logic
│   ├── game_state.py         ← State models
│   ├── config_loader.py      ← YAML config reader
│   └── message_types.py      ← Message protocol
├── cv/                       ← Computer Vision pipeline
│   ├── landmark_extractor.py ← MediaPipe hand detection
│   ├── skeleton_renderer.py  ← 128x128 skeleton image renderer
│   ├── model.py              ← Lightweight CNN (15 classes)
│   ├── inference.py          ← Real-time inference + stability check
│   ├── data_collector.py     ← Training data capture tool
│   └── train.py              ← Model training script
├── client/                   ← React + Vite frontend
│   └── src/
│       ├── App.jsx            ← Main app (Lobby → Calibration → Game)
│       ├── hooks/             ← WebSocket, WebRTC, GameState hooks
│       └── components/        ← All UI components
├── models/                   ← Saved CNN weights
└── data/                     ← Training data (gitignored)
```

## Quick Start

### 1. Install Dependencies

```bash
# Backend
cd server && pip install -r requirements.txt

# CV pipeline
cd cv && pip install -r requirements.txt

# Frontend
cd client && npm install
```

### 2. Collect Training Data

```bash
cd cv
python data_collector.py
```

- Use number keys (0-9) and letters (a-e) to select classes
- SPACE to capture frames, 's' for auto-save
- Collect ~100-200 samples per class

### 3. Train the CNN

```bash
cd cv
python train.py --data ../data --epochs 30
```

### 4. Start the Server

```bash
cd server
python main.py
```

### 5. Start the Frontend

```bash
cd client
npm run dev
```

### 6. Play!

1. Open http://localhost:5173 in two browser tabs
2. Enter names and join the same room
3. Complete calibration
4. Battle!

## Gameplay

- **Turn-based**: Only the active player can perform actions
- **Hand signs**: Perform real hand signs in front of your webcam
- **Buffer**: Build a sequence of up to 6 signs
- **Ram (🐏)**: Activate your sign sequence → execute jutsu
- **Scrap (❌)**: Clear buffer without ending turn
- **Shadow Clone (👥)**: Immediate, bypasses buffer
- **Focus (🧘)**: Activate with empty buffer → gain +20 chakra
- **Passive regen**: +10 chakra per turn

## Configuration

Edit `config/game.yaml` to tune all balance values:
- Jutsu damage, chakra costs, miss rates, cooldowns
- Buff/debuff effects and durations
- Passive regen, focus bonus, penalties
- Max buffer length, max buffs/debuffs
