---
name: cs4s-code-documentation
description: Strict rules for writing, maintaining, and formatting source code documentation and educational notes in the CS4S repository.
---

# CS4S Code Documentation Standard

CS4S is an educational project. The source code is part of the product. Documentation is not optional and its quality is equal to implementation quality. Assume the reader is a Computer Science student or junior developer.

## Zero-Tolerance Policy
- **No missing documentation**: Every module, class, and public method must be documented.
- **No AI-generated filler**: Comments must justify their existence. Do not merely repeat what the code does.
- **No redundant or placeholder comments**: Remove TODOs that replace explanations.
- **Documentation must be timeless**: No roadmap references, ticket numbers, or temporary migration notes.

## 1. Module Documentation
Every source file must contain a module-level docstring at the top explaining:
- Purpose
- Responsibility
- Architectural role
- Dependencies
- Expected collaborators
- Important implementation notes (when applicable)

## 2. Class Documentation
Every public class must have a docstring explaining:
- Why the class exists.
- What responsibility it owns.
- What responsibility it deliberately does **not** own.

## 3. Method Documentation
Every public method (and complex protected methods) must explain:
- Purpose.
- Inputs.
- Outputs.
- Side effects.
- Failure behavior (when relevant).

Do not repeat obvious implementation details.

## 4. Educational Notes
Every complex algorithm or critical engineering decision must contain an `Educational Note` block.
These notes should explain:
- Why the algorithm exists and why it is implemented this way.
- Common misconceptions and engineering trade-offs.
- Networking concepts (when applicable).
- Educational notes should teach concepts rather than describe syntax.

## 5. Consistency and Tone
- Documentation must follow a single repository-wide style (terminology, tone, formatting).
- Tone should be educational, technical, and rigorous but accessible to students.
- Remove historical implementation notes, commented-out code, and obsolete architecture references.
