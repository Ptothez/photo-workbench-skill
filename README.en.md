# Give every photo a clear place

[简体中文](README.md) | [English](README.en.md)

Photos arrive from phones, cameras and scans. Which still need sorting, which need editing, and which belong in a theme or a book? This Skill helps an AI Agent understand your goals, then build a local workbench for browsing photos, following progress and making decisions.

Your categories, retention limits and taste come first. Feedback keeps your original words and the action taken. Reusable lessons become active rules only after your adoption and evidence from multiple situations.

## Install and begin

```bash
npx -y skills add Ptothez/photo-workbench-skill -g --all
```

Tell your Agent:

> Help me build a photography workbench for family records and future photo books. First confirm where photos come from, what to keep, how I select them, and which decisions need me.

The Agent reads existing context and asks only what affects the design. It creates the workbench after you confirm the plan, without copying the author's personal categories or rules.

## Everyday use

- See incoming photos, sorting and editing progress, and who acts next.
- Open your themes or collections, browse individual previews, enlarge them and locate the exact original file.
- Use one review entry with separate queues for decisions needed now, missing information, optional checks and external clues. Agent-verifiable work stays with the Agent.
- Read a concrete question, choose or comment, save and move on. Saved decisions, actions awaiting execution and completed work remain distinct.
- Apply photo feedback to photos; keep sources for workflow and taste lessons, then propose, adopt and validate reusable rules.

## Browser or Windows desktop

The browser option needs Python 3.10+ and uses a standard-library local service. The optional Windows desktop host manages its own window and service, reconnects after service failure, and supports desktop and taskbar reopening. It creates no photo watcher or scheduled sorting job.

Desktop builds need Windows x64, the .NET Framework 4.8 compiler, Python and WebView2 Runtime. The build downloads a pinned SDK from official NuGet and verifies SHA-256. Only source is published. See [quickstart](skills/photo-workbench/references/quickstart.md) and [Windows desktop instructions](skills/photo-workbench/references/windows-desktop.md).

## Scope and checks

This is a Skill and local interface for work performed by your Agent. Actual image inspection, classification, preview generation, verified copying and archiving require the Agent and your authorization. An empty page or a filename guess is not completed selection. RAW, PSD and high-bit-depth scans need suitable preview tools.

```bash
python skills/photo-workbench/scripts/test_runtime.py -q
```

Synthetic tests cover confirmed creation, overwrite refusal, four review lanes, feedback persistence, conflict rejection, next-run context, cache invalidation and desktop options. The desktop source is also compiled on Windows. Exact file location, pinned-icon reopening, previews and interruption recovery must still be accepted on each user's machine. All Agent clients and operating systems are not claimed as tested.

No real photos, conversations, identities, private rules, databases, storage addresses or credentials are included. Data stays in your chosen local folder; the server binds only to loopback.

MIT; see [LICENSE](LICENSE).
