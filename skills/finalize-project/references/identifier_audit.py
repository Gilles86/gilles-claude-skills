#!/usr/bin/env python
"""Whole-tree identifier audit for a data release (generic template).

Run on the UPLOAD tree right before uploading, and again after any change.
Zero findings = clean. Everything it flags is a finding to fix or to
consciously accept (write the acceptance down).

    python identifier_audit.py <tree> \
        --names names.txt            # private list of names to grep for (one per line); NOT in the repo
        --approved qc_approved.tsv   # defacing QC approvals (column `path`, relative to <tree>)
        --domain example.edu         # your institution's DNS domain, to catch hostnames
        --out findings.tsv

What it checks (see deidentification.md for why):
  1. file-type allowlist            — a stray zip / PDF / .DS_Store / notebook is a finding
  2. text files                     — names, dates, times, e-mails, absolute paths, hostnames, IPs
  3. binaries                       — printable strings in the head and tail (gzip-aware); NIfTI text fields
  4. JSON key inventory             — printed once for you to read; denylisted keys are findings
  5. high-res 3D volumes            — every volume with voxels < HIRES_MM must be QC-approved

Adjust ALLOWED_*, DENY_KEYS and the regexes to the dataset; keep the structure.
"""
import argparse
import gzip
import json
import os
import re
import sys

import numpy as np

HIRES_MM = 1.5                    # voxel size below which a 3D volume counts as "anatomical"
HEAD_BYTES = 4 * 1024 * 1024      # how much of a binary to scan at the start
TAIL_BYTES = 1 * 1024 * 1024      # ... and at the end (MGZ tags, NIfTI extensions can sit there)

ALLOWED_NAMES = {'README', 'README.md', 'CHANGES', 'LICENSE', '.bidsignore',
                 'participants.tsv', 'participants.json', 'dataset_description.json'}
ALLOWED_SUFFIXES = ('.nii.gz', '.nii', '.json', '.tsv', '.tsv.gz', '.bvec', '.bval',
                    '.gii', '.mgz', '.label', '.annot', '.h5', '.txt', '.md')
TEXT_SUFFIXES = ('.json', '.tsv', '.txt', '.md', '.bvec', '.bval', '.csv', '.yml', '.yaml',
                 '.log', '.html', '.svg', '.xfm', '.lta', '.bidsignore')
NIFTI_TEXT_FIELDS = ('descrip', 'aux_file', 'db_name', 'intent_name')

DENY_KEYS = {'AcquisitionTime', 'AcquisitionDateTime', 'PatientName', 'PatientID',
             'PatientBirthDate', 'PatientSex', 'PatientWeight', 'InstitutionAddress',
             'DeviceSerialNumber', 'StationName', 'ProcedureStepDescription',
             'SeriesInstanceUID', 'StudyInstanceUID', 'ImageComments', 'OperatorName'}

PATTERNS = {
    'date_iso':   re.compile(r'\b(?:19|20)\d{2}[-/.](?:0[1-9]|1[0-2])[-/.](?:0[1-9]|[12]\d|3[01])\b'),
    'date_eu':    re.compile(r'\b(?:0[1-9]|[12]\d|3[01])[-/.](?:0[1-9]|1[0-2])[-/.](?:19|20)\d{2}\b'),
    'date_text':  re.compile(r'\b\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+(?:19|20)\d{2}\b', re.I),
    'time':       re.compile(r'\b(?:[01]\d|2[0-3]):[0-5]\d:[0-5]\d\b'),
    'email':      re.compile(r'[\w.+-]+@[\w-]+\.[\w.-]+'),
    'abs_path':   re.compile(r'(?:/Users/|/home/|/data/|/shares/|/scratch/|/storage/|[A-Z]:\\\\)[\w./\\-]*'),
    'ipv4':       re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b'),
}


def build_patterns(names, domain):
    pats = dict(PATTERNS)
    if domain:
        pats['hostname'] = re.compile(r'\b[\w.-]+\.(?:' + re.escape(domain) + r'|local)\b', re.I)
    names = [n.strip() for n in names if len(n.strip()) >= 3]
    if names:
        pats['name'] = re.compile(r'\b(?:' + '|'.join(re.escape(n) for n in names) + r')\b', re.I)
    return pats


def read_head_tail(fn):
    """Return (head, tail) bytes; gzip-decompressed when the file is gzipped."""
    if fn.endswith('.gz'):
        with gzip.open(fn, 'rb') as f:
            head = f.read(HEAD_BYTES)
            tail = b''
            # decompress the rest only when the file is small enough to bother
            if os.path.getsize(fn) < 256 * 1024 * 1024:
                rest = f.read()
                tail = rest[-TAIL_BYTES:]
        return head, tail
    with open(fn, 'rb') as f:
        head = f.read(HEAD_BYTES)
        size = os.path.getsize(fn)
        if size > HEAD_BYTES:
            f.seek(max(HEAD_BYTES, size - TAIL_BYTES))
            tail = f.read()
        else:
            tail = b''
    return head, tail


def scan_text(text, pats, path, findings, kind):
    for pname, pat in pats.items():
        for m in pat.finditer(text):
            s, e = max(0, m.start() - 30), min(len(text), m.end() + 30)
            findings.append(dict(path=path, kind=kind, pattern=pname, match=m.group(0),
                                 context=text[s:e].replace('\n', ' ').replace('\t', ' ')))


def scan_binary_strings(fn, rel, pats, findings):
    head, tail = read_head_tail(fn)
    for blob in (head, tail):
        for run in re.finditer(rb'[\x20-\x7e]{6,}', blob):
            scan_text(run.group(0).decode('ascii', 'replace'), pats, rel, findings, 'binary-strings')


def check_volume(fn, rel, approved, findings):
    """NIfTI/MGZ: text fields must be empty; hi-res 3D volumes must be QC-approved."""
    import nibabel as nib
    img = nib.load(fn)
    hdr = img.header
    if isinstance(img, nib.Nifti1Image):
        for field in NIFTI_TEXT_FIELDS:
            val = hdr[field].tobytes().strip(b'\x00')
            if val:
                findings.append(dict(path=rel, kind='nifti-header', pattern=field,
                                     match=val.decode('ascii', 'replace'), context=''))
    shape, zooms = img.shape, hdr.get_zooms()
    is_3d = len(shape) == 3 or (len(shape) == 4 and shape[3] == 1)
    if is_3d and min(zooms[:3]) < HIRES_MM and rel not in approved:
        findings.append(dict(path=rel, kind='hires-volume', pattern=f'voxel<{HIRES_MM}mm',
                             match=f'{shape} {tuple(round(float(z), 2) for z in zooms[:3])}',
                             context='not in the QC-approved list'))


def walk_keys(obj, out):
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.add(k)
            walk_keys(v, out)
    elif isinstance(obj, list):
        for v in obj:
            walk_keys(v, out)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('tree')
    ap.add_argument('--names', help='text file with one name per line (keep it private)')
    ap.add_argument('--approved', help='TSV with a `path` column of QC-approved anatomicals (relative to tree)')
    ap.add_argument('--domain', help='institution DNS domain, e.g. example.edu')
    ap.add_argument('--out', default='identifier_findings.tsv')
    args = ap.parse_args()

    names = open(args.names).read().splitlines() if args.names else []
    pats = build_patterns(names, args.domain)
    approved = set()
    if args.approved:
        import pandas as pd
        df = pd.read_csv(args.approved, sep='\t')
        if 'approved' in df.columns:
            df = df[df['approved'].astype(str).str.lower().isin(['true', '1', 'yes'])]
        approved = set(df['path'].astype(str))

    findings, json_keys, n_files = [], set(), 0
    for root, dirs, files in os.walk(args.tree):
        dirs.sort()
        for name in sorted(files):
            fn = os.path.join(root, name)
            rel = os.path.relpath(fn, args.tree)
            n_files += 1
            lname = name.lower()
            allowed = name in ALLOWED_NAMES or lname.endswith(ALLOWED_SUFFIXES)
            if name.startswith('._') or name == '.DS_Store' or name.startswith('.') and name not in ALLOWED_NAMES:
                allowed = False
            if not allowed:
                findings.append(dict(path=rel, kind='filetype', pattern='not-allowlisted', match=name, context=''))
            if lname.endswith('.nii') or lname.endswith('.nii.gz') or lname.endswith('.mgz'):
                check_volume(fn, rel, approved, findings)
                scan_binary_strings(fn, rel, pats, findings)
            elif name in ALLOWED_NAMES or lname.endswith(TEXT_SUFFIXES) or lname.endswith('.tsv.gz'):
                opener = gzip.open if lname.endswith('.gz') else open
                with opener(fn, 'rt', errors='replace') as f:
                    text = f.read()
                scan_text(text, pats, rel, findings, 'text')
                if lname.endswith('.json'):
                    try:
                        obj = json.loads(text)
                    except json.JSONDecodeError as e:
                        findings.append(dict(path=rel, kind='json', pattern='invalid', match=str(e), context=''))
                        continue
                    keys = set()
                    walk_keys(obj, keys)
                    json_keys |= keys
                    for k in sorted(keys & DENY_KEYS):
                        findings.append(dict(path=rel, kind='json-key', pattern='denylist', match=k, context=''))
            else:
                scan_binary_strings(fn, rel, pats, findings)

    import pandas as pd
    out = pd.DataFrame(findings, columns=['path', 'kind', 'pattern', 'match', 'context'])
    out.to_csv(args.out, sep='\t', index=False)
    print(f'{n_files} files scanned, {len(out)} findings -> {args.out}')
    if len(out):
        print(out.groupby(['kind', 'pattern']).size().to_string())
    print('\nJSON keys seen (read this list once):')
    print(' '.join(sorted(json_keys)))
    sys.exit(1 if len(out) else 0)


if __name__ == '__main__':
    main()
