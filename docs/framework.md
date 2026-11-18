# The framework: conducting AI in any course

**In one sentence.** A course is AI ready when, in the discipline's own work, students conduct AI: they frame the problem before prompting, delegate bounded work, audit what comes back before and after an independent check, add what only they can, sign for the result, and keep an honest record of how it happened.

This is Nik Bear Brown's framework, drawn from his courses *Conducting AI*, *Irreducibly Human*, *Computational Skepticism for AI* and *Prompt Engineering for Generative AI*, from the Frictional process log and from Medhavy's Glimmers. It is institution-neutral. Where a university has its own AI-ready requirements (Northeastern's Edge five standards, `standards/northeastern-edge.md`), they are an optional profile on top; section 9 shows the Northeastern crosswalk.

The toolkit suggests; it never decides. Every suggestion goes to the course team, who accept it, reject it, rewrite it, or add their own.

## The six readiness questions

The audit asks these of every course, and every suggestion names the ones it strengthens. They separate real AI readiness from trivial AI use.

| # | Question | What a yes looks like |
|---|---|---|
| R1 | **Clear rules for AI use and disclosure** | The syllabus says what students may and may not use AI for and why, how to disclose it, and how the instructor used AI to prepare the course |
| R2 | **Students attempt the learning first** | Where the skill is the point, students try it before AI; each module says what AI should and should not do (the phase gate) |
| R3 | **Hands-on AI work in the discipline** | At least one activity has students use AI on this course's real tasks, with bounded delegation (literacy: a fixed request; fluency: their own framing) |
| R4 | **Students judge and verify AI output** | Students audit the output before checking it, then verify against independent evidence; nobody accepts an answer because it reads well |
| R5 | **The process is recorded and graded** | An honest record of attempts, friction and AI contributions (the Frictional log, a sign-off) counts toward the grade |
| R6 | **Assessment shows learning AI cannot fake** | Students must explain, predict, defend or audit on their own: explanation on request, paper or oral checks, prediction-locks, planted-flaw audits |

A course can answer all six at the literacy level or the fluency level (section 6).

---

## 1. Why conducting, not using

- **The conductor plays no instrument** and still holds the whole: hears the wrong note before the score confirms it, chooses the piece, decides the interpretation. AI has augmented every instrument; the podium is still empty (*Conducting AI*, ch. 1).
- **Solving and verifying are different work.** AI makes producing cheap. Checking stays expensive and human, and the gap grows with scale. The answer is never "automate the verification" (*Conducting AI*, ch. 2; *Computational Skepticism*, ch. 1). This is a working wager, not a theorem.
- **The fluency trap.** The better an output looks, the less checking it invites, and fluency inflates confidence in your own evaluation.
- **You cannot audit what you do not know.** Students must still learn the fundamentals well enough to evaluate and transfer them. "Deprioritization is not deletion": offload the task, keep the skill to audit it (*Irreducibly Human*, Tier 1).
- **You cannot hand it the consequence.** A person signs. Accountability is why the human stays on the podium.

So AI readiness is not tool operation. A course that only teaches students to operate AI teaches the half that is getting cheaper.

## 3. The five supervisory capacities

The work only the conductor can do. Every suggestion names at least one. The right-hand column is how each looks in a course that is not about AI.

| Capacity | What it is | In any discipline |
|---|---|---|
| **Plausibility auditing** (PA) | Judging an output *before* checking it: is it plausible, what would I look up, why. Audit first: verdict, then target, then mechanism, before any lookup | Students read an AI answer in their field and say what is wrong or suspicious, and why, before they check |
| **Problem formulation** (PF) | Reframing from what is common and likely to what is salient and important, before the tool is engaged. Handing the problem over is abdication, not delegation | Students write their own framing, constraints and values before they prompt; they test whether two framings need different solutions |
| **Tool orchestration** (TO) | Choosing the lowest-autonomy tool the step needs, routing arithmetic and lookups out of the language model, checking a generative claim with a non-generative tool. Each handoff states what is passed, what it is trusted to be, and how that trust was earned | Students choose between a calculator, a database, a primary source, a lab protocol and a model, and say why |
| **Interpretive judgment** (IJ) | Supplying meaning and legitimacy the model cannot: AI can be useful, cannot stand behind what is right, and counterfeits what is trustworthy | Students turn "what the AI produced" into a recommendation they defend and sign (Memo A to Memo B) |
| **Executive integration** (EI) | Holding the threads together so later work can reopen earlier work; re-engaging on an event, not an attitude | Students name what would make them revisit a decision, and do it when it happens |

Bear's three levels of AI use describe a *task*, not a course: **copy editor** (output checkable at a glance), **research assistant** (correctness lives in sources you must consult), **supercollaborator** (output shapes the framing itself). The danger is "Level III work, Level I habits". Every suggested AI activity says which level it is and fits the checking to it.

## 4. The module spine

Bear's courses share one contract per module, and it transfers to any subject (the repository versions of INFO 6205 Algorithms and CSYE 7270 game development already use it; a course's live Canvas export may not, so audit what is there):

**Predict → Build It → Use It → Ship It → Verify**

1. **Predict.** Before anything runs: the expected result, confidence, assumptions, and what would prove it wrong. Dated, and never rewritten (the *prediction-lock*). A wrong honest prediction costs nothing.
2. **Build It.** The student's own first attempt, before AI, and an explanation of the mechanism.
3. **Use It.** AI joins under a stated division of labour (below). Runs are labelled: fixture, simulation, live.
4. **Ship It.** The work goes out with its record: predictions, who did what, the Frictional log, a sign-off.
5. **Verify.** Against evidence independent of the generator. Agreement between models is not an independent check.

Each module states its **phase gate** as two lines, specific to that module's task:

> **AI should:** …  
> **Human should:** …

and asks students to **record the split** (what actually happened, not what was planned). Each task gets one of three verdicts: **deprioritize** (AI may take it), **supervise** (AI drafts, the student checks), **protect** (the student does it; this is the learning).

Each module ends with three **ungraded Assessments**: produce the artifact and run its checks; explain one mechanism and one limit without the AI's phrasing; answer one misconception question (answer hidden).

## 5. The moves

These are the building blocks the toolkit suggests. Each has a template in `templates/`. A course rarely needs all of them; section 8 says how to choose. A suggestion the tool cannot build (fixing a notebook, changing an exam) is still a suggestion: it carries an implementation brief (`templates/brief.md`) for a coding agent or a person.

| Move | What the instructor gets | Strengthens (Edge) | Template |
|---|---|---|---|
| **AI use policy** | Syllabus section: students may use AI and are expected to; use alone is not misconduct; you must be able to explain your work; never invent effort, results or approvals; how to disclose. Plus the instructor's own use in preparing the course, written by the instructor | R1 (E1) | `policy.md` |
| **Module objective** | One objective per chosen module that names AI and a capacity: "Audit an AI-generated [domain artifact] for [failure] before checking it against [source]" | R3, R4 (E2) | `objective.md` |
| **Phase gate** | The AI should / Human should lines and "record the split" for a module | R2 (E3) | `phase-gate.md` |
| **Conduct exercise** | End-of-module exercise: frame → delegate a bounded task (level named) → audit first → independent check → Memo B (what the AI produced, what I add, why it can be trusted, why it is right here, signed recommendation) → sign-off with "Not checked" | R3, R4 (E3, E4) | `conduct-exercise.md` |
| **Glimmer** | An ill-structured generative assignment: students make something original with AI, then defend their process and evaluate the output; graded on process, judgment and the AI Use Disclosure. Variant: an AI output built to fail if accepted, done under a prediction-lock | R3, R4, R5 (E3–E5) | `glimmer.md` |
| **Frictional log** | A process record added to graded work, worth 10% of each assignment: attempts, friction and response, human and AI contributions, learning and uncertainty, traceable process (2/1/0 each). Struggle is the point; invented struggle earns nothing | R5 (E5) | `frictional.md`, `frictional-rubric.json` |
| **Planted-flaw audit** | An assessment (quiz, exam, discussion) showing an AI output with one planted flaw: find the unsupported claim, name it in course terms, say the check, rewrite the instruction, state the consequence. Works on paper with no AI in the room | R4, R6 (E4) | `planted-flaw-audit.md` |
| **Sign-off** | A block at the end of submitted work: what was checked, how, what was not checked, what is not claimed, signed or withheld | R4, R5 (E4, E5) | `sign-off.md` |
| **Process criteria** | Rubric criteria that grade the quality of AI engagement: framed before prompting, audited before checking, checked independently, kept and rejected with reasons, disclosed honestly | R5 (E5) | `process-criteria.json` |
| **Ungraded Assessments** | The three end-of-module checks above, for courses whose modules end without practice | R2, R6 | `module-assessments.md` |

Optional, offer and never impose: **Relative Quartile** (20% comparative grading, because AI raises everyone's first draft), **the confession** (find and report a mistake in your own work), **the verb audit** (the verb in each conclusion must match its evidence: suggest, show, demonstrate, prove).

## 6. Literacy and fluency

Two levels (Northeastern's Edge uses the same words):

- **AI literacy** = students evaluate AI output, the weight is on the audit. The designated activity has students run a **fixed, bounded request** you give them (the same prompt for everyone, on this module's task) and grades their audit of what came back. Planted-flaw audits, Glimmers of the "built to fail" kind and Memo B on a supplied Memo A are literacy practice too.
- **AI fluency** = students conduct AI on the discipline's own tasks. Conduct exercises with their own framing and delegation, Glimmers of the generative kind, tool orchestration choices, Level II and III delegation with their checks.

**R3, and Edge's E3, need students to engage with an AI tool themselves.** An AI output written for the exercise (constructed and labelled) is good practice for E4, but on its own it does not meet E3: pair it with an activity where students run the tool. With no student tool access, say so to the instructor: E3 cannot be met without it.

Neither is better. Most graduate courses start at literacy. A course already using AI in its work, a studio or a capstone, fits fluency. The toolkit proposes a level from the evidence and the instructor decides.

## 7. Rules the suggestions keep

1. **Nothing invented.** No made-up effort, results, approvals, quotes or statistics in drafts. Examples are labelled constructed. The instructor's own AI use is a blank for the instructor to fill; the toolkit never writes it for them.
2. **No AI detectors.** The framework grades the process the student shows, not a guess about authorship.
3. **Attempt before AI** wherever the module's skill is the point (*protect*). Where it is not, say so (*deprioritize*).
4. **Independent checks only.** A second model agreeing is not verification.
5. **Explain on request.** Students must be able to explain anything they submit; that is the authorship test.
6. **The discipline's own work.** "No generic prompts": an exercise uses the course's real content, data and tasks, not a generic AI activity bolted on.
7. **Frameworks, not findings.** The seven tiers of *Irreducibly Human*, the Boondoggle Score and the Weave are Bear's frameworks; they are presented as such. Statistics Bear has flagged as unverified are not used.
8. **Respect the instructor's load.** Every rubric says how long it takes to grade. Large classes get lighter versions (fewer Frictional rows, peer review of sign-offs).

## 8. Choosing suggestions for one course

1. **Read the course as it is.** Subject, level, audience, how modules end, what is graded and how, what the syllabus says about AI.
2. **Answer every readiness question first.** The smallest set that gives each of R1–R6 a yes: usually the policy, one designated activity (Conduct exercise or Glimmer) with its judging step, process criteria on its rubric, a phase gate where the skill must be protected, and one assessment AI cannot fake. If the institution has a profile, make sure this set also meets its standards (for Northeastern: add a module objective naming AI). Call this the *core path*.
3. **Then deepen, module by module.** A phase gate and an end-of-module exercise where the module's content gives AI something real to do. Skip modules where it does not; say why.
4. **Add Frictional to graded work** where the course grades products only.
5. **Fit the audience.** Translate capacities into the discipline's words. Match tool access (chat only, institutional Claude, none). Undergraduates get more scaffolding and shorter logs; professionals get Level III delegation.
6. **Stay small.** A suggestion the instructor can review in minutes beats one that rewrites a module. Twelve good suggestions beat forty.

## 9. Crosswalk to Northeastern's dimensions and Edge's standards (an example profile)

| Framework element | Dimension | Edge standard |
|---|---|---|
| Plausibility auditing, audit first, planted-flaw audit, verb audit | D2 Critical thinking and judgment | E4 |
| Problem formulation, values in the constraint set | D4 Human creativity, D3 Ethical use | E2, E3 |
| Tool orchestration, three levels of use, solve-verify asymmetry | D1 Understanding AI and data | E2, E3 |
| Interpretive judgment, Memo B, the signature | D3 Ethical and responsible use | E4 |
| Executive integration, re-engagement | D4 Human creativity | E3 |
| Policy and disclosure, no invented records | D3 | E1 |
| Frictional log, process criteria, sign-off | D2, D3 | E5 |
| Glimmer | D2, D4 | E3, E4, E5 |

## Sources

Bear's course repositories: `info-7375-conducting-ai` (chapters 1–15, `NEU-COURSE-TEMPLATE.md`, `prerequisites/`), `info-7375-irreducibly-human`, `info-7375-computational-skepticism-for-ai`, `info-7375-prompt-engineering-for-generative-ai` (`docs/concept-spine.md`), the `frictional/` module in each, `csye-7270-building-virtual-environments/teaching-foundation.md`, and the Glimmers convention in the Medhavy cancer textbooks.
