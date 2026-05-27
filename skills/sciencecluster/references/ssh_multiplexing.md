# SSH connection reuse (multiplexing)

**When to load:** you're scripting many `ssh <cluster-alias> '...'`
calls in a row (e.g., a poll loop, a batch of `rsync`s), or you're
getting transient connection refusals from the login host.

Cluster SSH rate-limits new connections — many fresh `ssh
<cluster-alias> '...'` calls in a row get blocked. Multiplexing
reuses one persistent connection, kinder on the shared login cap.

One-time `~/.ssh/config` (replace `<cluster-alias>` with the user's
alias name):

```
Host <cluster-alias>
    ControlMaster auto
    ControlPath ~/.ssh/cm/%r@%h:%p
    ControlPersist 60m
```

`mkdir -p ~/.ssh/cm`. Tear down with `ssh -O exit <cluster-alias>`.
