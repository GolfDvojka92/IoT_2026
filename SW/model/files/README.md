# Baby Cry Detection – CNN Model

Binarni klasifikator audio događaja koji razlikuje **plač bebe** (BabyCry) od ostalih zvukova (Other), baziran na konvolucionoj neuronskoj mreži treniranoj na Mel-spektrogram + MFCC karakteristikama.

---

## Struktura projekta

```
.
├── dataset/
│   ├── train/          ← WAV fajlovi + features.npz (posle preprocesiranja)
│   ├── validation/
│   └── test/
├── development set/
│   ├── train.tsv
│   └── validation.tsv
├── evaluation set/
│   └── test.tsv
├── model/
│   ├── preprocess.py   ← ekstrakcija karakteristika iz WAV fajlova
│   ├── model.py        ← CNN arhitektura
│   ├── train_model.py  ← petlja za trening
│   └── infer.py        ← inferencija i evaluacija
├── requirements.txt
└── README.md
```

---

## Instalacija

```bash
pip install -r requirements.txt
```

---

## Korak 1 – Preuzimanje audio fajlova

```bash
python download_audioset_baby_cry_dataset.py
```

WAV fajlovi treba da se nađu u `dataset/train/`, `dataset/validation/`, `dataset/test/`.

---

## Korak 2 – Preprocesiranje

Čita TSV anotacije, seče audio segmente prema `onset`/`offset` vrednostima i čuva numpy karakteristike:

```bash
python model/preprocess.py
```

Generiše `features.npz` u svakom dataset folderu.

---

## Korak 3 – Trening

```bash
python model/train_model.py --epochs 30 --batch-size 64 --lr 0.001
```

| Argument | Default | Opis |
|---|---|---|
| `--epochs` | 30 | Broj epoha |
| `--batch-size` | 64 | Veličina mini-batch-a |
| `--lr` | 0.001 | Početni learning rate |

Čuva:
- `model/best_model.pt` – checkpoint s najboljim val F1 skorom  
- `model/training_log.csv` – metrike po epohama

---

## Korak 4 – Inferencija i evaluacija

### Jedan audio fajl
```bash
python model/infer.py --audio put/do/audio.wav
```

Primer izlaza:
```
── Rezultat ──────────────────────────────
  Fajl              : audio.wav
  prediction        : BabyCry
  baby_cry_prob     : 0.8731
  other_prob        : 0.1269
  n_windows         : 6
─────────────────────────────────────────
```

### Evaluacija test seta
```bash
python model/infer.py --eval
```

### Prilagođeni prag
```bash
python model/infer.py --eval --threshold 0.6
```

---

## Arhitektura modela

```
Ulaz: (B, 1, 104, T)  [Mel-spektrogram + MFCC]
  ↓
ConvBlock(1→32)   [Conv3×3 → BN → ReLU] × 2 → MaxPool(2×2) → Dropout
  ↓
ConvBlock(32→64)  [Conv3×3 → BN → ReLU] × 2 → MaxPool(2×2) → Dropout
  ↓
ConvBlock(64→128) [Conv3×3 → BN → ReLU] × 2 → MaxPool(2×2) → Dropout
  ↓
GlobalAveragePooling
  ↓
Linear(128→256) → ReLU → Dropout(0.5)
  ↓
Linear(256→2)   [logiti]
```

**Karakteristike ulaza** (za svaki segment od 1 sekunde):
- 64 Mel-frekvencijske ose
- 40 MFCC koeficijenata  
- Ukupno: 104 frekvencijska kanala

**Tehničke napomene:**
- `WeightedRandomSampler` + ponderisana `CrossEntropyLoss` za nebalansirane klase  
- `CosineAnnealingLR` raspored učenja  
- Gradient clipping (max_norm=5.0)
- `GlobalAveragePooling` čini model invarijantnim na dužinu ulaza

---

## Format TSV podataka

| Kolona | Opis |
|---|---|
| `filename` | Ime WAV fajla (npr. `audio_30.wav`) |
| `event_label` | `BabyCry` ili `Other` |
| `onset` | Početak događaja u sekundama |
| `offset` | Kraj događaja u sekundama |
| `start` | Apsolutni početak u originalnom snimku |
| `name` | Identifikator YouTube videa |
| `original_label` | Originalna AudioSet labela |
