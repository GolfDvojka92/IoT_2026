import os
import argparse
import subprocess
import pandas as pd
from tqdm import tqdm
import yt_dlp

def main(args):
    data_type = args.data_type
    workspace = args.workspace

    data_path = os.path.join(workspace, 'dataset', data_type)
    os.makedirs(data_path, exist_ok=True)

    if data_type in ['train', 'validation']:
        csv_path = os.path.join(workspace, 'development set', f'{data_type}.tsv')
    elif data_type == 'test':
        csv_path = os.path.join(workspace, 'evaluation set', f'{data_type}.tsv')

    df = pd.read_csv(csv_path, sep='\t')
    distinct_files = df['name'].unique()
    distinct_set = [(x, df['start'].loc[df['name'] == x].unique()[0]) for x in distinct_files]
    print(f'Broj jedinstvenih fajlova: {len(distinct_set)}')

    error_count = 0
    ydl_opts = {'format': 'bestaudio', 'quiet': True, 'noplaylist': True}

    for name, start in tqdm(distinct_set):
        url = f'https://www.youtube.com/watch?v={name}'
        out_wav = os.path.join(data_path, f'{name}_{int(start)}.wav')

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                stream_url = info['url']

            cmd = [
                'ffmpeg', '-y',
                '-ss', str(int(start)),
                '-t', '10',
                '-i', stream_url,
                '-ar', '16000',
                out_wav
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode != 0:
                error_count += 1
                print(f'Greška kod ffmpeg za {name}: {result.stderr[-500:]}')
            elif not os.path.exists(out_wav):
                error_count += 1
                print(f'wav fajl nije kreiran za {name}')

        except Exception as e:
            error_count += 1
            print(f'Nije moguće preuzeti {name}: {e}')

    print('Broj fajlova koji nisu preuzeti:', error_count)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Extract AudioSet Dataset')
    parser.add_argument('--workspace', type=str, required=True)
    parser.add_argument('--data_type', type=str, required=True, choices=['train', 'validation', 'test'])
    args = parser.parse_args()
    main(args)