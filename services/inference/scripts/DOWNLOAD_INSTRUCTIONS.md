# CC-CEDICT Download Instructions

## Automatic Download (Recommended)

The automatic download scripts are currently experiencing issues with source URLs. Please use the manual method below.

## Manual Download

### Option 1: MDBG.net (Official Source)

1. Visit: https://www.mdbg.net/chinese/dictionary?page=cedict
2. Scroll to the "Download" section
3. Click on **"CEDICT (UTF-8)"** download link
4. Save the file as: `cedict_ts.u8`
5. Move the file to: `services/inference/data/cedict_ts.u8`

### Option 2: GitHub Mirror

1. Visit: https://github.com/gumblex/cedict-mirror
2. Click on the `cedict_ts.u8` file
3. Click "Raw" button to download
4. Save to: `services/inference/data/cedict_ts.u8`

### Option 3: NPM Package

```bash
npm install cc-cedict
cp node_modules/cc-cedict/cedict_ts.u8 services/inference/data/
```

## Verification

After downloading, verify the file:

```bash
cd services/inference/data
python -c "import os; print(f'File size: {os.path.getsize(\"cedict_ts.u8\") / (1024*1024):.2f} MB')"
```

Expected size: ~9-10 MB

Count lines:

```bash
python -c "with open('cedict_ts.u8', 'r', encoding='utf-8') as f: print(f'Lines: {len(f.readlines()):,}')"
```

Expected lines: ~110,000-120,000

## Next Steps

Once you have the file, convert it to JSON:

```bash
cd services/inference/scripts
python convert_cedict.py ../data/cedict_ts.u8 --output ../data/cc_cedict.json
```

## Demo Dictionary

For immediate testing, a small demo dictionary is provided in:
- `services/inference/data/demo_cedict.json` (100 common characters)

You can use this while waiting for the full dictionary download.

