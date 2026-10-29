# Give Your Photos a Clear Place

[简体中文](README.md) | [English](README.en.md)

Photos arrive from phones, cameras, and film scans. Which need sorting or editing? Which belong in a series or a future photobook? This skill helps your AI understand your goals first, then build a photography workbench for browsing, progress, and decisions.

It does not copy the author's family categories, album themes, or taste. Your comments remain intact, with a record of what was done. Reusable experience becomes a rule only after you adopt it and it is tested across different situations.

## Install and Start

```bash
npx -y skills add Ptothez/photo-workbench-skill -g --all
```

Then ask your AI:

> Build a photography workbench for me. I want to preserve family memories and develop photo series. First confirm where my photos come from, what to keep, how I select pictures, and which decisions need my input.

The AI should read existing material and ask only about gaps that affect the design. It creates your workbench after you confirm the plan.

## Everyday Use

- See incoming photos, sorting and editing progress, and who handles the next step.
- Browse collections and themes, then individual photos. Enlarge a photo or locate its exact file.
- Review everything in one queue: view the photos, understand the question and suggestion, make a decision, and continue.
- Apply photo-specific corrections to those photos. Keep broader workflow and aesthetic rules separate, with original feedback, adoption, validation, and activation records.

## What Is Included

A building and acceptance skill, a feedback protocol, an adaptable interface, and a local reference server using the Python standard library. The bootstrap script requires a confirmed needs profile and refuses to overwrite an existing directory. The default trigger is an explicit user message, not a background watcher.

This is not an automatic photo editor with an embedded AI model. Your AI Agent must inspect actual images and implement classification, archiving, and learning within your authorization. An empty page or working API is not proof that photo selection is finished.

## Requirements and Checks

A Skills-capable AI client and Python 3.10+. The UI has no build dependencies. Your Agent must choose and validate suitable preview tools for RAW, PSD, and high-bit-depth scans in your environment.

```bash
python skills/photo-workbench/scripts/test_runtime.py -q
```

Synthetic tests cover confirmed initialization, overwrite protection, saved feedback, conflict rejection, and reading feedback in a later execution context. Native file navigation, app windows, and visual acceptance still require testing on the user's system.

No personal photos, chats, identities, private rules, databases, storage addresses, or credentials are included. Your data stays in your chosen local directory. The server binds only to loopback.

MIT. See [LICENSE](LICENSE).
