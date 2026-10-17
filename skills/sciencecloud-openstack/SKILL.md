---
name: sciencecloud-openstack
description: UZH ScienceCloud VMs driven through the OpenStack API instead of clicking through the web console — checking whether a box is up and what its IP is now, spinning up a CPU or T4 box with a data volume for a pipeline run (e.g. defacing / staging an OpenNeuro release, a JAX fit), getting a BIDS dataset onto it, and tearing it down so it stops costing money. Covers application-credential auth (so Claude can run it non-interactively), the shared group project (colleagues' VMs listed next to yours), busy flavors that fail with "No valid host was found", volumes that outlive their server, and rebuilt boxes with new host keys. Use whenever the user wants to start, stop, rebuild, list or delete a ScienceCloud VM, a box is unreachable, an SSH alias looks stale, a dataset needs to go onto a VM, or `openstack`, `openrc`, `clouds.yaml` or cloud.science-it.uzh.ch come up. Pairs with **sciencecluster** (SLURM — a different system).
---

# UZH ScienceCloud — driving VMs through the OpenStack API

ScienceCloud VMs are plain Ubuntu boxes: no SLURM, no shared filesystem, every
box its own island. Until now the only way to boot, reboot, rebuild or look up
the IP of one was the web console (<https://cloud.science-it.uzh.ch/>), which
meant that every time a box was unreachable the answer was "go check the
console". ScienceCloud is stock OpenStack, though, so all of that works from the
command line — and, with an application credential, Claude can do it itself.

**Verified end-to-end 2026-09-16** (pilot for the neural_priors OpenNeuro
release): credential auth → list → launch → attach and mount a volume → SSH in →
build a conda env → copy a subject → full teardown.

Cloud-wide constants are baked in verbatim. Per-user values are `<angle-bracket>`
placeholders filled in from private config (the user's global CLAUDE.md or
private notes). **VM IPs, project names and inventories never go in a public
repo** — refer to boxes by SSH alias.

## Constants

| Thing | Value |
|---|---|
| Web console | <https://cloud.science-it.uzh.ch/> (UZH network / VPN) |
| API (Keystone v3) | `https://cloud.science-it.uzh.ch:5000` (UZH network / VPN) |
| Network | `uzh-only` — private `172.23.x.y` address, reachable over the VPN, no floating IP needed |
| Security group | `default` (SSH + ping) |
| Login user | `ubuntu`, passwordless sudo, no swap |
| Root disk | 100 GB on every flavor — datasets go on a volume |
| Flavors | `<N>cpu-<M>ram-hpcv3\|hpcv4[-gpuT4\|-gpuL4\|-lmem]` |
| Images | decorated and re-dated, e.g. `***Ubuntu 24.04 (2026-05-08)` — use the UUID |

Placeholders:

- `<cloud>` — cloud name in `clouds.yaml` (the downloaded file calls it `openstack`)
- `<keypair>` — your key pair name in the project
- `<vm>` / `<uuid>` / `<vol-uuid>` — a VM name, a server UUID, a volume UUID
- `<alias>` — the VM's SSH alias in `~/.ssh/config`

Every command below assumes:

```bash
export OS_CLOUD=<cloud>
O=~/venvs/openstack/bin/openstack
ME=$($O token issue -f value -c user_id)     # doubles as the auth smoke test
```

## Golden rules

**1. Authenticate with an application credential, never the password.** The
`<project>-openrc.sh` from the console does `read -sr` for the UZH password.
Claude cannot answer that prompt and should never be handed the password
anyway. An application credential is scoped to one project, has an expiry, and
is revoked with one click. (Setup below.)

**2. The project is shared with the whole group.** `server list` and
`volume list` show everyone's VMs and volumes — on 2026-09-16 about fifteen
VMs from half a dozen people, several with names close to ours. So: list with
`--user $ME`, and **act only by UUID**, never by name or pattern. Names are not
unique and a typo lands on a colleague's box.

**3. Only deleting stops the bill.** A shut-off VM still reserves (and is billed
for) its hardware. S3IT advises against pause / suspend / shelve — boxes often
fail to come back. So a pilot box is either running something or deleted.

**4. Volumes outlive their server** (`delete_on_termination: False`). Deleting a
VM leaves its volume `available`, still counting against quota. Several such
orphans were sitting in the project. Delete the volume explicitly — after
checking it holds nothing we need.

**5. Confirm with the user before any delete or rebuild.** Both wipe the root
disk irreversibly. Launching is cheap; destroying is not.

**6. An unreachable box is not a dead box.** Check its state first
(`server show`, `console log show`), then suspect a stale IP in `~/.ssh/config`
or a new host key after a rebuild. Only conclude it is gone when
`server show <uuid>` says `No Server found`.

## One-time setup

```bash
python3 -m venv ~/venvs/openstack
~/venvs/openstack/bin/pip install python-openstackclient openstacksdk
```

The application credential is made by the user in the console (~2 min):
**Identity → Application Credentials → Create**. Name it (e.g. after the
machine it lives on), set an expiry a few months out, leave roles empty. On the
confirmation page click **Download clouds.yaml** — the secret is shown once.

```bash
mkdir -p ~/.config/openstack
mv ~/Downloads/clouds.yaml ~/.config/openstack/clouds.yaml
chmod 600 ~/.config/openstack/clouds.yaml
```

Never `cat` it into a transcript; redact when inspecting:
`sed -E 's/(secret|password)(:).*/\1\2 <redacted>/' ~/.config/openstack/clouds.yaml`.
Write the expiry date into private notes — a `401` months later is otherwise a
mystery.

## Recipes

### Is the box up, and what is its IP now?

```bash
$O server list --user $ME -c ID -c Name -c Status -c Networks -c Flavor
```

`Networks` reads `{'uzh-only': ['172.23.x.y']}`. If that differs from the
`Hostname` in `~/.ssh/config`, the box was rebuilt or relaunched: update the
alias, and clear the old host key (`ssh-keygen -R <old-ip>`) — the VM got a new
one. `Status` other than `ACTIVE`? `server show <uuid> -f value -c status -c fault`
says why, and `console log show --lines 40 <uuid>` shows whether it booted.

A VM that disappears from the list is really gone: `--deleted` is admin-only and
silently ignored, and a deleted server's event log cannot be read. The console
is the place to ask who did it.

### Spin up a box for a pipeline run

Pick the flavor for the job, not the biggest one:

- **Per-subject CPU pipelines** (defacing, staging, QC — `xargs -P N` over
  subjects): `8cpu-32ram-hpcv3` or `15cpu-60ram-hpcv3`, plus a data volume.
- **JAX / PyMC-on-GPU fits**: a `-gpuT4` flavor. One job per box (15 GB VRAM,
  JAX preallocates 75 %). T4 is compute capability 7.5: fp16 yes, **bfloat16 no**.
- **hpcv4 and gpuL4 are often full.** On 2026-09-16 an `8cpu-32ram-hpcv4` launch
  failed with `No valid host was found. There are not enough hosts available.`;
  the identical hpcv3 flavor launched immediately. S3IT publishes a flavor
  availability report (VPN) — look before picking v4.

```bash
IMG=$($O image list -f value -c ID -c Name | awk '/Ubuntu 24.04/{print $1; exit}')
$O server create --wait --flavor 8cpu-32ram-hpcv3 --image $IMG \
    --network uzh-only --security-group default --key-name <keypair> \
    <vm> -f value -c id -c status -c addresses
```

A failed launch still leaves a VM in `ERROR` holding a quota slot — delete it by
UUID before retrying. Match a project key pair to a local key with
`ssh-keygen -E md5 -lf ~/.ssh/id_rsa.pub` against `keypair list`.

`ACTIVE` comes in under a minute; SSH works about a minute after `create`
returns. Add the alias, then wait for it:

```bash
for i in $(seq 20); do
  ssh <alias> -o ConnectTimeout=5 -o StrictHostKeyChecking=accept-new true && break
  sleep 10
done
```

A fresh image has **no NVIDIA driver** and **no conda**: install the driver on
GPU boxes (`sudo apt install nvidia-driver-580-server-open`, reboot) and put
miniforge on the data volume (`/data/miniforge3`), then build envs from the
repo's YAML under `nohup`.

### Give it a data volume

```bash
VOL=$($O volume create --size 250 <vm>-data -f value -c id)
$O server add volume <uuid> $VOL          # showed up as /dev/sdb — check lsblk
ssh <alias> 'sudo mkfs.ext4 -q -L data /dev/sdb &&
  sudo mkdir -p /data &&
  echo "LABEL=data /data ext4 defaults,nofail 0 2" | sudo tee -a /etc/fstab &&
  sudo mount /data && sudo chown ubuntu:ubuntu /data'
```

`mkfs` **only on a brand-new volume** — on a reattached one it erases the data.
Mount by `LABEL`: device letters differ between hypervisor generations (`sdb` on
some boxes, `vdb` on others), and `nofail` keeps the box bootable if the volume
is ever detached.

### Get a dataset onto it

In order of preference:

1. **Swap a volume.** The native way to move data between VMs:
   `server remove volume` on the box that has it, `server add volume` on the new
   one, mount. Minutes regardless of size. A volume attaches to one VM at a time.
2. **Box-to-box copy.** VMs have no SSH keys to each other; give the target a
   dedicated key authorised on the source, then `rsync`/`tar` directly inside
   the cloud.
3. **Relay through the laptop** (`ssh A 'tar cf - …' | ssh B 'tar xf - -C /data'`)
   only for small things: over the VPN it managed ~13 MB/s (7.8 GB in 10 min).

Which copy to take from matters: the laptop's `/data/ds-*` working copies may
be partial (on neural_priors it held one preprocessed BOLD run per session; the
release needed all sixteen), and the cluster share can hang outright (a plain
`df` on `/shares/...` never returned on 2026-09-16). Check completeness at the
source before shipping — count the files the pipeline asserts on. Use
`tar czhf` (dereference) for anything under a BIDS/git-annex tree, and compare
file counts on both sides afterwards.

### Tear it down

```bash
$O server show <uuid> -f value -c name -c volumes_attached     # look first
$O server delete --wait <uuid>
$O volume delete <vol-uuid>                                     # after the user OKs it
$O server show <uuid>; $O volume show <vol-uuid>                # both: "No ... found"
ssh-keygen -R <ip>                                              # the IP gets reused
```

Then remove the `Host <alias>` block from `~/.ssh/config`.

`server delete --wait` printed `Error deleting server: <uuid>` and exited
non-zero **although the delete worked** — the wait loop trips over the vanished
server. Verify with `server show`, don't retry. Volume deletion is asynchronous:
`deleting` for ~10–30 s, then not found.

### Rebuild

`$O server rebuild --image <image-uuid> <uuid>` reinstalls the OS: root disk
wiped, attached volumes kept. The box comes back with a **new host key** and
**no NVIDIA driver**. Our own history shows the IP is not reliably kept either
(two GPU boxes rebuilt on 2026-08-27 came back on new addresses, one without its
separate volume) — re-read it with `server list` and fix the alias.

## Troubleshooting

| Symptom | Cause |
|---|---|
| Timeout connecting to `:5000` | VPN is down |
| `Missing value auth-url required for auth plugin password` | `OS_CLOUD` unset, or `clouds.yaml` not in `~/.config/openstack/` |
| `401 … requires authentication` | application credential expired or revoked — make a new one |
| VM `ERROR`, fault `No valid host was found` | flavor class full — delete it, pick hpcv3 |
| `ACTIVE` but SSH times out | still booting (`console log show`), wrong key pair, or stale IP in the alias |
| `REMOTE HOST IDENTIFICATION HAS CHANGED` | box was rebuilt — confirm with `server show` (`updated`), then `ssh-keygen -R <ip>` |
| `No Server found` for a box that was just listed | it was deleted, possibly by a co-owner in the console |
| Quota exceeded on create | `ERROR` VMs and orphaned `available` volumes count — `limits show --absolute` |

For anything not covered here, `openstack <noun> --help` is complete, and the
Python SDK takes the same auth: `openstack.connect(cloud="<cloud>")`.
