#!/usr/bin/env python
"""Apply a defacing mask at the raw-voxel level, verify, compute QC metrics, render a report.

Generic template (see defacing.md). The defacing tool's output is used ONLY to
derive the mask; the released image is the staged original with masked voxels
zeroed in the stored datatype and a header copied byte-for-byte (free-text
fields blanked). That makes the release provably identical to the original
outside the face.

    python deface_apply_qc.py \
        --undefaced   WORK/undefaced/sub-01_ses-1_run-1_T1w.nii.gz \
        --defaced-ref WORK/pydeface/sub-01_ses-1_run-1_T1w_defaced.nii.gz \   # or --mask <binary 1=remove>
        --out         WORK/defaced/sub-01_ses-1_run-1_T1w.nii.gz \            # copied to TARGET only after approval
        --brain-mask  WORK/brainmask_rawgrid/sub-01_ses-1_run-1_desc-brain_mask.nii.gz \   # optional, in the undefaced grid
        --png         WORK/qc/sub-01_ses-1_run-1_T1w.png \
        --metrics     WORK/qc/metrics.tsv

Exit code 1 when verification fails or brain voxels were removed.
"""
import argparse
import gzip
import io
import os

import nibabel as nib
import numpy as np

NIFTI_TEXT_FIELDS = ('descrip', 'aux_file', 'db_name', 'intent_name')
FRAC_LOW, FRAC_HIGH = 0.02, 0.35     # frac_head_removed outside this band is suspicious
DILATE = 3                           # voxels; "near-brain" warning zone


def read_raw(fn):
    opener = gzip.open if fn.endswith('.gz') else open
    with opener(fn, 'rb') as f:
        return f.read()


def apply_mask_bytewise(src, dst, mask):
    """Write dst = src with mask voxels zeroed in the stored dtype; header/extensions byte-identical
    except the free-text fields, which are blanked. gzip mtime=0 so nothing about *when* leaks."""
    raw = read_raw(src)
    hdr = nib.Nifti1Header.from_fileobj(io.BytesIO(raw), check=False)
    for field in NIFTI_TEXT_FIELDS:
        hdr[field] = b''
    vox_offset = int(hdr['vox_offset'])
    dtype, shape = hdr.get_data_dtype(), hdr.get_data_shape()
    n = int(np.prod(shape)) * dtype.itemsize
    arr = np.frombuffer(raw[vox_offset:vox_offset + n], dtype=dtype).reshape(shape, order='F').copy()
    assert mask.shape == arr.shape[:3], (mask.shape, arr.shape)
    arr[mask] = 0
    os.makedirs(os.path.dirname(dst) or '.', exist_ok=True)
    tmp = dst + '.part'
    with open(tmp, 'wb') as fh:
        with gzip.GzipFile(fileobj=fh, mode='wb', mtime=0) as gz:
            gz.write(hdr.binaryblock)
            gz.write(raw[348:vox_offset])
            gz.write(arr.tobytes(order='F'))
            gz.write(raw[vox_offset + n:])
    os.replace(tmp, dst)


def verify(src, dst, mask):
    """Geometry, dtype, scaling identical; kept voxels identical; removed voxels zero; text fields empty."""
    a, b = nib.load(src), nib.load(dst)
    assert a.shape == b.shape, (a.shape, b.shape)
    assert a.get_data_dtype() == b.get_data_dtype()
    assert np.array_equal(a.header.get_qform(), b.header.get_qform())
    assert np.array_equal(a.header.get_sform(), b.header.get_sform())
    sa, sb = a.header.get_slope_inter(), b.header.get_slope_inter()
    assert sa == sb or all(x is None or np.isnan(x) for x in sa + sb), (sa, sb)
    ua = np.asanyarray(a.dataobj.get_unscaled())
    ub = np.asanyarray(b.dataobj.get_unscaled())
    keep = ~mask
    assert np.array_equal(ua[keep], ub[keep]), 'kept voxels differ'
    assert not np.any(ub[mask]), 'removed voxels not zero'
    for field in NIFTI_TEXT_FIELDS:
        assert not b.header[field].tobytes().strip(b'\x00'), field
    return ua


def derive_mask(undefaced, defaced_ref, eps=1e-6):
    """mask = voxels the defacing tool zeroed. Requires the same grid."""
    u, d = nib.load(undefaced), nib.load(defaced_ref)
    assert u.shape[:3] == d.shape[:3], (u.shape, d.shape)
    assert np.allclose(u.affine, d.affine, atol=1e-3), 'defaced reference is not on the undefaced grid'
    ud = np.asanyarray(u.dataobj)
    dd = np.asanyarray(d.dataobj)
    if ud.ndim == 4:
        ud, dd = ud[..., 0], dd[..., 0]
    return (np.abs(ud) > 0) & (np.abs(dd) <= eps)


def otsu(values):
    hist, edges = np.histogram(values, bins=256)
    centers = (edges[:-1] + edges[1:]) / 2
    w0 = np.cumsum(hist); w1 = w0[-1] - w0
    m0 = np.cumsum(hist * centers) / np.maximum(w0, 1)
    m1 = (np.cumsum((hist * centers)[::-1])[::-1] / np.maximum(w1, 1))
    between = w0[:-1] * w1[:-1] * (m0[:-1] - m1[1:]) ** 2
    return centers[np.argmax(between)]


def metrics(data, mask, brain=None):
    from scipy import ndimage
    x = data.astype(np.float64)
    nz = x[x > 0]
    head = x > otsu(nz) if nz.size else np.zeros_like(mask)
    out = dict(n_removed=int(mask.sum()),
               frac_head_removed=float((mask & head).sum() / max(head.sum(), 1)))
    if brain is not None:
        out['brain_removed'] = int((mask & brain).sum())
        dil = ndimage.binary_dilation(brain, iterations=DILATE)
        out['brain_removed_dilated'] = int((mask & dil).sum())
    out['flag'] = ';'.join(f for f, c in [
        ('face-maybe-left', out['frac_head_removed'] < FRAC_LOW),
        ('over-aggressive', out['frac_head_removed'] > FRAC_HIGH),
        ('BRAIN-CLIPPED', out.get('brain_removed', 0) > 0),
        ('near-brain', out.get('brain_removed_dilated', 0) > 0)] if c)
    return out


def load_brain_mask(fn, ref_img):
    """Brain mask must be on the undefaced grid. If it is not, resample by header (nearest);
    for fMRIPrep masks prefer bringing them over with the from-orig_to-T1w transform first
    (see defacing.md) — header resampling only works when both sforms describe the same world."""
    m = nib.load(fn)
    if m.shape[:3] != ref_img.shape[:3] or not np.allclose(m.affine, ref_img.affine, atol=1e-3):
        from nilearn.image import resample_to_img
        print('WARNING: brain mask not on the undefaced grid; resampling by header (nearest)')
        m = resample_to_img(m, ref_img, interpolation='nearest')
    return np.asanyarray(m.dataobj) > 0


def report_png(undefaced_img, before, after, mask, png, title):
    """Before/after sagittal + coronal MIPs, mid-sagittal slice with removed region, axial slice through the cut."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    canon = nib.as_closest_canonical(nib.Nifti1Image(before.astype(np.float32), undefaced_img.affine))
    b = np.asanyarray(canon.dataobj)
    a = np.asanyarray(nib.as_closest_canonical(nib.Nifti1Image(after.astype(np.float32), undefaced_img.affine)).dataobj)
    m = np.asanyarray(nib.as_closest_canonical(nib.Nifti1Image(mask.astype(np.uint8), undefaced_img.affine)).dataobj) > 0
    vmax = np.percentile(b[b > 0], 99.5) if (b > 0).any() else 1
    x_mid = b.shape[0] // 2
    z_cut = int(np.argmax(m.sum(axis=(0, 1)))) if m.any() else b.shape[2] // 3

    fig, ax = plt.subplots(2, 4, figsize=(16, 8))
    panels = [
        ('Sagittal MIP', lambda v: v.max(axis=0).T),
        ('Coronal MIP', lambda v: v.max(axis=1).T),
        ('Mid-sagittal slice', lambda v: v[x_mid].T),
        (f'Axial slice z={z_cut}', lambda v: v[:, :, z_cut].T),
    ]
    for j, (name, fn) in enumerate(panels):
        for i, (label, vol) in enumerate([('before', b), ('after', a)]):
            ax[i, j].imshow(fn(vol), cmap='gray', vmin=0, vmax=vmax, origin='lower')
            ax[i, j].set_title(f'{name} — {label}', fontsize=9)
            ax[i, j].axis('off')
        # removed region overlay on the "after" row
        overlay = np.ma.masked_where(~fn(m).astype(bool), fn(m.astype(float)))
        ax[1, j].imshow(overlay, cmap='autumn', alpha=0.5, origin='lower')
    fig.suptitle(title, fontsize=10)
    fig.tight_layout()
    os.makedirs(os.path.dirname(png) or '.', exist_ok=True)
    fig.savefig(png, dpi=90)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--undefaced', required=True)
    ap.add_argument('--defaced-ref', help='defacing tool output on the same grid (used only to derive the mask)')
    ap.add_argument('--mask', help='explicit binary mask (1 = remove) on the same grid')
    ap.add_argument('--out', required=True)
    ap.add_argument('--brain-mask')
    ap.add_argument('--png')
    ap.add_argument('--metrics')
    args = ap.parse_args()

    u_img = nib.load(args.undefaced)
    if args.mask:
        m_img = nib.load(args.mask)
        assert np.allclose(m_img.affine, u_img.affine, atol=1e-3)
        mask = np.asanyarray(m_img.dataobj) > 0
    else:
        mask = derive_mask(args.undefaced, args.defaced_ref)

    apply_mask_bytewise(args.undefaced, args.out, mask)
    before = verify(args.undefaced, args.out, mask)
    after = before.copy(); after[mask] = 0
    brain = load_brain_mask(args.brain_mask, u_img) if args.brain_mask else None
    met = metrics(before, mask, brain)
    met['verify_ok'] = True
    met['path'] = args.out
    print({k: (round(v, 4) if isinstance(v, float) else v) for k, v in met.items()})

    if args.png:
        report_png(u_img, before, after, mask, args.png,
                   f"{os.path.basename(args.out)}  head-removed={met['frac_head_removed']:.3f}  "
                   f"brain-removed={met.get('brain_removed', 'n/a')}  {met['flag']}")
    if args.metrics:
        import pandas as pd
        row = pd.DataFrame([met])
        header = not os.path.exists(args.metrics)
        row.to_csv(args.metrics, sep='\t', index=False, mode='a', header=header)
    raise SystemExit(1 if met.get('brain_removed', 0) > 0 else 0)


if __name__ == '__main__':
    main()
