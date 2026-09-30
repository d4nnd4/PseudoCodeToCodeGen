"""
Este es el catálogo de lenguajes destino y prompts específicos para cada uno.

Tener en cuenta que desde acá se pueden extender plantillas para los prompts necesarios.

"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Language:
    id: str
    label: str
    extension: str
    monaco: str  # id de lenguaje para el editor Monaco
    guidelines: str
    example: str = ""


BASE_SYSTEM_PROMPT = """You are a senior software engineer that translates pseudocode into \
production-quality source code.

Rules:
- Output ONLY the source code. No explanations before or after it.
- Do NOT wrap the answer in markdown fences.
- Implement exactly the logic described by the pseudocode, keeping the same order of steps.
- Use clear names derived from the pseudocode. Short comments are allowed where they help.
- If the pseudocode reads input or prints output, do the same using the idiomatic
  standard-library mechanism of the target language.
- The program must compile / run as-is.

Target language: {label}
{guidelines}
"""

LANGUAGES: dict[str, Language] = {
    "python": Language(
        id="python",
        label="Python 3.12",
        extension="py",
        monaco="python",
        guidelines="""- Use type hints and functions.
- Put the entry point under `if __name__ == "__main__":`.
- Only use the standard library.""",
    ),
    "go": Language(
        id="go",
        label="Go 1.22",
        extension="go",
        monaco="go",
        guidelines="""- Produce a single file with `package main` and a `func main()`.
- Only use the standard library; include every import you use and no unused imports.
- Handle errors explicitly.""",
    ),
    "typescript": Language(
        id="typescript",
        label="TypeScript 5 (Node.js)",
        extension="ts",
        monaco="typescript",
        guidelines="""- Strict typing: no `any`.
- Target Node.js; for console input use `node:readline/promises`.
- Wrap the entry point in an async `main()` function and call it.""",
    ),
    "rpgle": Language(
        id="rpgle",
        label="ILE RPG (RPGLE) for IBM i / AS400",
        extension="rpgle",
        monaco="rpgle",
        guidelines="""- Use fully free-format RPG (**FREE on the first line).
- Declare everything with DCL-S, DCL-DS, DCL-PR, DCL-PI, DCL-PROC.
- Use `ctl-opt dftactgrp(*no) actgrp(*caller);`.
- Use DSPLY for simple console output/input (messages up to 52 chars).
- Use %char, %dec, %int, %trim, %len, etc. built-in functions.
- End the main program with `*inlr = *on;` and `return;`.
- Never use fixed-format columns (no C-specs, D-specs or F-specs in fixed form).""",
        example="""Example of the expected style:
**FREE
ctl-opt dftactgrp(*no) actgrp(*caller);

dcl-s total packed(9:2) inz(0);
dcl-s i int(10);
dcl-s msg char(52);

for i = 1 to 10;
  total += i;
endfor;

msg = 'Total: ' + %char(total);
dsply msg;

*inlr = *on;
return;""",
    ),
}


def build_system_prompt(lang: Language) -> str:
    prompt = BASE_SYSTEM_PROMPT.format(label=lang.label, guidelines=lang.guidelines)
    if lang.example:
        prompt += "\n" + lang.example + "\n"
    return prompt


def build_user_prompt(pseudocode: str, lang: Language) -> str:
    return (
        f"Translate the following pseudocode into {lang.label}.\n\n"
        f"PSEUDOCODE:\n{pseudocode.strip()}\n\n"
        f"{lang.label} CODE:"
    )
