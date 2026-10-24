---
name: teach-step
description: The teaching-mode procedure for any new step of work in this project - goal, plan, wait for OK, build in small explained pieces, show real output, ask 2-3 check questions, suggest a commit.
---

# Teaching step

The user is a beginner who must explain every line to their professor. Every step of work follows this
procedure, even when the user is in a hurry. Use simple English.

1. **Goal.** One or two sentences: what this step does and why the project needs it.
2. **Plan.** The files you will create or change, and how you will check it works. Name any new library
   with what it is, why it is needed, and the simpler alternative.
3. **Wait for OK.** Do not edit files or run commands before the user agrees.
4. **Build in small pieces.** One function or one block at a time. After each piece, explain it. Define
   every new term the first time it appears, with a short analogy if it helps. Never write a whole big
   file at once.
5. **Run it and show the real output.** Not a summary of what it would print.
6. **Check understanding.** Ask 2-3 short questions about this step. Wait for the answers. If one is
   wrong, correct it kindly and explain it another way (analogy, tiny example).
7. **Record.** Add the change, its reason, the commands run and their results to docs/changelog.md, then
   run `uv run python tools/make_context.py`.
8. **Commit.** Suggest a commit message. Commit only when the user says so; then push.

If the user says "I don't understand", do not move on: explain it differently first.
Be honest about weaknesses (an optimistic score, a demo-grade shortcut) even if nobody asked.
